# GitLab API
*Version: 0.0.1*

GitLab API Python Wrapper

Includes a large variety of API calls to GitLab

This repository is actively maintained and will continue adding more API calls

### API Calls:
- Branches
- Commits
- Deploy Tokens
- Groups
- Members
- Merge Request
- Merge Rules
- Packages
- Pipeline
- Projects
- Protected Branches
- Runners
- Users

### Usage:
```python
#!/usr/bin/python
# coding: utf-8
import gitlab_api

token = "<GITLAB_TOKEN/PERSONAL_TOKEN>"
client = gitlab_api.Api(token=token)

users = client.get_users()
print(users)

created_merge_request = client.create_merge_request(project_id=123, source_branch="development", 
                                                    target_branch="production",title="Merge Request Title")
print(created_merge_request)
```

#### Build Instructions
Build Python Package

```bash
sudo chmod +x ./*.py
pip install .
python setup.py bdist_wheel --universal
# Test Pypi
twine upload --repository-url https://test.pypi.org/legacy/ dist/* --verbose -u "Username" -p "Password"
# Prod Pypi
twine upload dist/* --verbose -u "Username" -p "Password"
```
