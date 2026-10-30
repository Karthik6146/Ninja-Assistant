import time
from ninja import db,assistant_events

def test_reminders_are_atomic_and_survive_duplicate_ticks():
    now=time.time();reminder=assistant_events.add('Check my video queue',now+1,'reminder-key')
    assert assistant_events.add('Check my video queue',now+1,'reminder-key')['id']==reminder['id']
    assert assistant_events.tick(now)==[]
    assert assistant_events.tick(now+2)==[reminder['id']]
    assert assistant_events.tick(now+3)==[]
    assert assistant_events.listing()[0]['state']=='due'

