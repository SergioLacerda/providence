""".providence/runtime/README.md sections: framework integration examples and memory
organization strategies. Split out of _runtime_readme_template.py to keep
files under the 200-line convention.
"""

from __future__ import annotations


def _integration_section() -> str:
    return """## Integration with Agent Frameworks

### With LangChain/LlamaIndex

```python
from langchain.memory import ConversationBufferMemory

# Store governance in agent memory
agent.memory['mandates'] = read_governance('mandates')
agent.memory['guidelines'] = read_governance('guidelines')

# Use in prompts
system_prompt = f'''
You follow SDD governance.

MANDATES:
{agent.memory['mandates']}

GUIDELINES:
{agent.memory['guidelines'][task_category]}
'''
```

### With Custom Agents

```python
class SDDAgent:
    def __init__(self, project_root):
        self.governance = {}
        self.load_governance(project_root)

    def load_governance(self, project_root):
        '''Load governance once at startup'''
        source_dir = Path(project_root) / '.providence' / 'source'

        self.governance['mandates'] = (source_dir / 'mandates' / 'mandates.md').read_text()
        self.governance['guidelines'] = {}

        for category_file in (source_dir / 'guidelines').glob('*.md'):
            category = category_file.stem
            self.governance['guidelines'][category] = category_file.read_text()

    def execute(self, task):
        '''Execute task with cached governance'''
        relevant_guideline = self.governance['guidelines'].get(task.category)
        # Use cached guideline
        return self.process_task(task, relevant_guideline)
```

## Memory Organization Strategy

### By Category (Recommended)

```
agent.memory = {
    'mandates': <mandates_content>,
    'guidelines': {
        'git': <git_guidelines>,
        'testing': <testing_guidelines>,
        'naming': <naming_guidelines>,
        'docs': <docs_guidelines>,
        'style': <style_guidelines>,
        'performance': <performance_guidelines>
    },
    'last_updated': <timestamp>,
    'cache_validity': 86400  # 24 hours in seconds
}
```

### By Usage Frequency (Alternative)

```
agent.memory = {
    'frequent': {
        'mandates': <mandates_content>,
        'git_guidelines': <git_guidelines>,
        'testing_guidelines': <testing_guidelines>
    },
    'occasional': {
        'naming_guidelines': <naming_guidelines>,
        'style_guidelines': <style_guidelines>
    },
    'reference': {
        'docs_guidelines': <docs_guidelines>,
        'performance_guidelines': <performance_guidelines>
    }
}
```

"""
