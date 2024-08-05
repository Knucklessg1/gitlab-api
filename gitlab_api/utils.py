#!/usr/bin/python
# coding: utf-8
import logging
from typing import Union, List, Any, Dict

from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.dynamic import AppenderQuery
import requests

try:
    from gitlab_api.gitlab_models import (
        Response,
    )
except ModuleNotFoundError:
    from gitlab_models import (
        Response,
    )

try:
    from gitlab_api.gitlab_db_models import (
        LabelsDBModel,
        LabelDBModel,
        TagDBModel,
        TagsDBModel,
        CommitDBModel,
        ParentIDDBModel,
        ParentIDsDBModel,
        ArtifactDBModel,
        ArtifactsDBModel,
    )
except ModuleNotFoundError:
    from gitlab_db_models import (
        LabelsDBModel,
        LabelDBModel,
        TagDBModel,
        TagsDBModel,
        CommitDBModel,
        ParentIDDBModel,
        ParentIDsDBModel,
        ArtifactDBModel,
        ArtifactsDBModel,
    )
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)


def process_response(response: requests.Response) -> Union[Response, requests.Response]:
    try:
        response.raise_for_status()
    except Exception as response_error:
        logging.error(f"Response Error: {response_error}")
    status_code = response.status_code
    raw_output = response.content
    headers = response.headers
    try:
        response = response.json()
    except Exception as response_error:
        logging.error(f"JSON Conversion Error: {response_error}")
    try:
        response = Response(
            data=response,
            status_code=status_code,
            raw_output=raw_output,
            json_output=response,
            headers=headers,
        )
    except Exception as response_error:
        logging.error(f"Response Model Application Error: {response_error}")

    return response


def remove_none_values(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def get_related_model(sqlalchemy_model, key, value):
    """Get the related SQLAlchemy model for a given key."""
    mapper = class_mapper(sqlalchemy_model)
    for prop in mapper.iterate_properties:
        if prop.key == key:
            return prop.mapper.class_
    raise ValueError(f"Unable to find related model for key: {key}")


def validate_list(list_object: List, session) -> List:
    related_models = [
        (
            pydantic_to_sqlalchemy(pydantic_model=item, session=session)
            if hasattr(item, "Meta") and hasattr(item.Meta, "orm_model")
            else item
        )
        for item in list_object
    ]
    print(f"\n\nRelated models: {related_models}")
    return related_models


def validate_dict(dictionary: Dict, parent_key: str, sqlalchemy_model: Any, session=None) -> Any:
    related_sqlalchemy_model = None
    mapper = class_mapper(sqlalchemy_model)
    for prop in mapper.iterate_properties:
        if prop.key == parent_key:
            related_sqlalchemy_model = prop.mapper.class_
    if not related_sqlalchemy_model:
        raise ValueError(f"Unable to find related model for key: {parent_key}")
    print(f"\n\nRelated instance: {related_sqlalchemy_model}")
    # Special handling for labels
    if related_sqlalchemy_model == LabelsDBModel:
        labels = []
        for label in dictionary["labels"]:
            labels.append(LabelDBModel(**label))
        if labels:
            labels_model = LabelsDBModel(labels=labels)
        else:
            labels_model = None
        return labels_model
    # Special handling for tags
    if related_sqlalchemy_model == TagsDBModel:
        tags = []
        for tag in dictionary["tags"]:
            tag = TagDBModel(**tag)
            session.add(tag)
            tags.append(tag)
            print(f"\n\nADDED TAG: {tag}")
        if tags:
            tags_model = TagsDBModel(tags=tags)
            session.add(tags_model)
        else:
            tags_model = None
        return tags_model
    if related_sqlalchemy_model == CommitDBModel:
        parent_ids = []
        for parent_id in dictionary["parent_ids"]["parent_ids"]:
            parent_ids.append(ParentIDDBModel(**parent_id))
        if parent_ids:
            parent_ids_model = ParentIDsDBModel(parent_ids=parent_ids)
        else:
            parent_ids_model = None
        print(f"\n\nCOMMIT TRAILERS: {related_sqlalchemy_model.trailers}")
        print(f"\n\nEXTENDED COMMIT TRAILERS: {related_sqlalchemy_model.extended_trailers}")

        setattr(related_sqlalchemy_model, "parent_ids", parent_ids_model)
    if related_sqlalchemy_model == ArtifactsDBModel:
        artifacts = []
        for artifact in dictionary["artifacts"]:
            artifacts.append(ArtifactDBModel(**artifact))
        if artifacts:
            artifacts_model = ArtifactsDBModel(artifacts=artifacts)
        else:
            artifacts_model = None
        return artifacts_model
    value = remove_none_values(dictionary)
    print(f"\n\nSetting Nested Model ({related_sqlalchemy_model}): {value}")
    nested_model = related_sqlalchemy_model(**value)
    print(f"\n\nObtained Nested Model: {nested_model}")
    related_model = pydantic_to_sqlalchemy(pydantic_model=nested_model, session=session)
    print(f"\n\nDefined SQLAlchemy: {related_model}")
    return related_model


def pydantic_to_sqlalchemy(pydantic_model, session):
    # Check if the model is already converted by ensuring the model doesn't have Meta pydantic field,
    # but does have base_type sqlalchemy field.
    if (
        not hasattr(pydantic_model, "Meta")
        or not hasattr(pydantic_model.Meta, "orm_model")
    ) and hasattr(pydantic_model, "base_type"):
        sqlalchemy_instance = pydantic_model
        print(f"\n\nFound SQLAlchemy Model on First Try: {sqlalchemy_instance}")
        return sqlalchemy_instance
    sqlalchemy_model = pydantic_model.Meta.orm_model
    sqlalchemy_instance = sqlalchemy_model()
    for key, value in pydantic_model.model_dump(exclude_unset=True).items():
        if value:
            if isinstance(value, list):
                print(f"\n\nValue that is a list: {value} for key: {key}")
                related_models = validate_list(list_object=value, session=session)
                setattr(sqlalchemy_instance, key, related_models)
                print(f"\n\nSQLAlchemy List Model Set: {related_models}")
            elif isinstance(value, dict):
                print(f"\n\nValue that is a dict: {value} for key: {key}")
                related_model = validate_dict(
                    dictionary=value, parent_key=key, sqlalchemy_model=sqlalchemy_model, session=session
                )
                print(f"\n\nSetting Related Model: {related_model} for {key}")
                setattr(sqlalchemy_instance, key, related_model)
                print(f"\n\nSQLAlchemy Dict Model Set: {related_model}")
            else:
                print(f"\n\nImmediately Setting Attribute: {value}")
                setattr(sqlalchemy_instance, key, value)
                print(f"\n\nImmediately Set Attribute: {value}")

    print(f"\n\nCompleted Conversion for: {sqlalchemy_instance}")
    return sqlalchemy_instance


def upsert(session, response):
    items = None
    for attribute_name in dir(response.data):
        if attribute_name.startswith("_"):
            continue
        attribute_value = getattr(response.data, attribute_name)
        if isinstance(attribute_value, list):
            items = attribute_value
    for item in items:
        print(f"Item: \n{item}\n\n")
        db_model = pydantic_to_sqlalchemy(pydantic_model=item, session=session)
        upsert_row(db_model=db_model, session=session)
    print("Items Added\n\nCommitting Session...")
    session.commit()


def upsert_row(session, db_model):
    if db_model is None:
        return None
    model_type = type(db_model)
    print(f"\n\nSearching for {db_model.id} in {model_type}")
    existing_model = session.query(model_type).filter_by(id=db_model.id).first()
    if existing_model:
        print(f"\n\nFound Existing Model: {existing_model}")
        try:
            for attr, value in db_model.__dict__.items():
                if attr != "_sa_instance_state":
                    setattr(existing_model, attr, value)
        except Exception as e:
            print(f"Unable to merge: {e}")
        print(f"Merged {model_type.__name__} with ID {existing_model.id}")
    else:
        for relation in db_model.__mapper__.relationships:
            related_model = getattr(db_model, relation.key)
            related_model_type = type(related_model)
            if isinstance(related_model, InstrumentedList):
                for item in related_model:
                    if item is not None:
                        existing_related = session.query(type(item)).get(item.id)
                        if existing_related is None:
                            session.add(item)
                        else:
                            related_model.remove(item)
                            related_model.append(existing_related)
            elif isinstance(related_model, AppenderQuery):
                pass
            elif related_model is not None:
                print(
                    f"\n\nFound Related Model ({related_model_type}): ID: {related_model.id} {related_model}"
                )
                existing_related = session.query(related_model_type).filter_by(id=related_model.id).first()
                print(
                    f"\n\nExisting Related Model ({related_model_type}): {existing_related}"
                )
                if existing_related is None:
                    print(f"\n\nADDING RELATED MODEL: {related_model}")
                    session.add(related_model)
                else:
                    print(f"\n\nUPDATING RELATED MODEL: {related_model}")
                    setattr(db_model, relation.key, existing_related)
            # elif related_model is not None and isinstance(related_model, Dict):
            #     validate_dict(dictionary=related_model, sqlalchemy_model=model_instance_type, parent_key=)
        # Add the new model instance
        print(f"\nSETTING EXISTING MODEL: {db_model}")
        existing_model = db_model
        session.add(existing_model)
        print(f"\nInserted new {model_type.__name__} with ID {existing_model.id}")

    try:
        session.commit()
        print("Committed Session!")
    except Exception as e:
        session.rollback()
        print(
            f"Error inserting/updating {model_type.__name__} with ID {db_model.id}: {e}"
        )
    return existing_model
