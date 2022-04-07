from typing import Dict, Tuple
from abc import ABC, abstractmethod
import re
from urllib.error import HTTPError

from ghapi.all import GhApi

from .config import set_config, Config
default_config = set_config()

class VersionControlManager(ABC):
    @abstractmethod
    def __init__(self, issue_number: int):
        pass

    @abstractmethod
    def get_comments(self) -> Dict:
        'Paginate through PR pages and fetch all comments'
        pass

    @abstractmethod
    def extract_hidden_variables(self, variables: list, prefix: str) -> Dict:
        '''Extracts (prefixed) variables from Github pull request.
        If variable has been defined (with template `<!-- PREFIX_VARIABLE=value -->` )
        more than once, last instance is taken.
        '''        
        pass

    @abstractmethod
    def add_label(self, label: str = 'Production') -> None:
        'Adds `label` to PR and removes it from all other issues that have it'
        pass

    @abstractmethod
    def create_comment(self, body: str) -> None:
        'Generic method to create PR comment'
        pass

    @abstractmethod
    def is_pr_diverged(self) -> bool:
        '''Returns True if no changes has been made to base branch 
        since issue has been branched
        '''
        pass

    @abstractmethod
    def is_pr_mergeable(self) -> bool:
        'Returns True if PR can be merged with the base branch.'
        pass

    @abstractmethod
    def merge_pr(self) -> Tuple[bool, str]:
        '''Merge PR with the base branch. If merged successfuly, return True.
        If failed, returns exception message.
        '''
        pass

    @abstractmethod
    def close_pr(self) -> Tuple[bool, str]:
        '''Closes the PR. Returns True if closed successfuly.
        If failed, returns exception message.
        '''
        pass

class DevelopmentDummyManager(VersionControlManager):
    def __init__(self, issue_number: int):
        self.issue_number = issue_number

    def get_comments(self) -> Dict:
        return {}

    def extract_hidden_variables(self, variables: list, prefix: str) -> Dict:
        return {}

    def add_label(self, label: str = 'Production') -> None:
        pass

    def create_comment(self, body: str) -> None:
        print(body)

    def is_pr_diverged(self) -> bool:
        return False

    def is_pr_mergeable(self) -> bool:
        return True

    def merge_pr(self) -> bool:
        return True, None

    def close_pr(self) -> bool:
        return True, None

class GithubManager(VersionControlManager):
    def __init__(self, issue_number: int, config: Config = default_config):
        self.issue_number = issue_number
        self.config = config
        self.github_api = self.initialize_github_api()
        
    def initialize_github_api(self):
        repo_conf = self.config.repository
        return GhApi(owner=repo_conf.owner, repo=repo_conf.name)

    def get_comments(self):
        comments = []
        page = 1
        while True:
            tmp_comments = self.github_api.issues.list_comments(self.issue_number, page=page)
            page += 1
            comments += tmp_comments
            if not tmp_comments:
                break
        return comments

    def extract_hidden_variables(self, variables: list, prefix: str) -> Dict:
        found_vars = {}
        for c in self.get_comments():
            for var in variables:
                if var in c.body:
                    found = re.findall(r'<!-- %s_%s=(.*?) -->' % (prefix, var), c.body, re.M)
                    if found:
                        found_vars[var] = found[0]
        return found_vars

    def _maybe_create_label(self, name: str) -> None:
        try:
            self.github_api.issues.get_label(name)
        except HTTPError as e:
            self.github_api.issues.create_label(name, color='d73a4a')

    def add_label(self, label: str = 'Production'):
        self._maybe_create_label(label)

        for i in self.github_api.issues.list(filter='all', labels=label):
            self.github_api.issues.remove_label(i.number, name=label)

        self.github_api.issues.add_labels(self.issue_number, labels=[label, ])

    def create_comment(self, body: str):
        self.github_api.issues.create_comment(
            self.issue_number, body,
            accept='application/vnd.github.v3.html+json')

    def is_pr_diverged(self):
        pr = self.github_api.pulls.get(self.issue_number)
        comp = self.github_api.repos.compare_commits(pr.head.ref, pr.base.ref)
        return True if comp.status == 'diverged' else False

    def is_pr_mergeable(self):
        pr = self.github_api.pulls.get(self.issue_number)
        return pr.mergeable

    def merge_pr(self) -> Tuple[bool, str]:
        try:
            self.github_api.pulls.merge(self.issue_number)
            return True, None
        except HTTPError as e:
            return False, e

    def close_pr(self) -> Tuple[bool, str]:
        try:
            self.github_api.pulls.update(self.issue_number, state='closed')
            return True, None
        except HTTPError as e:
            return False, e
