import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from turn_logic import TurnDetector

def feed(detector,probs,complete=lambda:0.9,wake=False):
    events=[]
    for p in probs:events+=detector.frame(p,complete,wake)
    return events

def test_speech_then_short_pause_ends_turn_when_smart_turn_says_complete():
    d=TurnDetector()
    events=feed(d,[.9]*20+[.05]*8)
    assert events[0]=='speech' and events[-1]=='turn'
    # 20 speech frames + ~200 ms of silence: the turn ends ~0.2 s after speech stops, not after a fixed 0.7 s.
    assert len([e for e in events if e=='turn'])==1

def test_incomplete_thought_waits_then_hard_timeout_ends_turn():
    d=TurnDetector()
    events=feed(d,[.9]*20+[.05]*20,complete=lambda:0.1)
    assert 'turn' not in events
    events=feed(d,[.05]*40,complete=lambda:0.1)
    assert events.count('turn')==1

def test_resumed_speech_cancels_pending_end():
    d=TurnDetector()
    events=feed(d,[.9]*20+[.05]*4+[.9]*20+[.05]*8)
    assert events.count('speech')==1 and events.count('turn')==1

def test_clicks_and_breaths_do_not_start_speech():
    d=TurnDetector()
    assert feed(d,[.9,.9,.05]*30)==[]

def test_standby_discards_turns_without_wake_word_and_keeps_those_with_it():
    d=TurnDetector(standby=True)
    assert feed(d,[.9]*20+[.05]*8)==['speech','discard']
    events=feed(d,[.9]*10,wake=True)+feed(d,[.9]*10+[.05]*8)
    assert events[-1]=='turn'

def test_reset_clears_partial_turn():
    d=TurnDetector()
    feed(d,[.9]*20)
    d.reset()
    assert feed(d,[.05]*80)==[]


def test_prestarted_process_runs_through_media_run_and_returns_output():
    import subprocess,sys,tempfile
    from ninja import media
    out,err=tempfile.TemporaryFile(),tempfile.TemporaryFile()
    waiting=subprocess.Popen([sys.executable,'-c','import sys;print("got",sys.stdin.readline().strip())'],stdin=subprocess.PIPE,stdout=out,stderr=err)
    waiting.stdin.write(b'job-1 2\n');waiting.stdin.close()
    assert media.run(['runner'],started=(waiting,out,err)).strip()=='got job-1 2'
