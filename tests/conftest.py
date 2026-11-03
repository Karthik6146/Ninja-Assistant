import os
import tempfile
os.environ['NINJA_DATA']=tempfile.mkdtemp(prefix='ninja-tests-')
os.environ['NINJA_TOKEN']='test-token'
# The suite covers Studio and YouTube too; tests/test_setup.py checks the public build without them.
os.environ.setdefault('NINJA_CREATOR','1')
os.environ['LANGCHAIN_TRACING_V2']='false'
import pytest
from ninja import db

@pytest.fixture(autouse=True)
def clean():
    db.init()
    with db.connect() as c:
        for table in ('projects','jobs','audit','preferences','approvals','publications','packages','youtube_operations','workspaces','templates','job_events','chat_usage','video_workflows','youtube_channels','studio_workflows','studio_runs','studio_files','studio_uploads','agent_tasks','agent_steps','assistant_memory','assistant_memory_fts','assistant_reminders','whatsapp_messages'): c.execute('DELETE FROM '+table)
