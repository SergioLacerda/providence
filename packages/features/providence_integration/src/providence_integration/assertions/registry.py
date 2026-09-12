"""Registry."""

from .config import ConfigHasKeyAssertion, ConfigIsValidPathAssertion
from .filesystem import FsExistsAssertion
from .git import GitHasCommitAssertion
from .process import ProcessExitAssertion, ProcessNotAllSkippedAssertion

REGISTRY = {
    "fs.exists": FsExistsAssertion,
    "config.has_key": ConfigHasKeyAssertion,
    "config.is_valid_path": ConfigIsValidPathAssertion,
    "process.exit_code": ProcessExitAssertion,
    "process.not_all_skipped": ProcessNotAllSkippedAssertion,
    "git.has_commit": GitHasCommitAssertion,
}
