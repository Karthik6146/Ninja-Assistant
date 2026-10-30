import sys
from . import db
from .worker import execute

if __name__=='__main__':
    # --wait: imports are done first; the worker sends "<job> <attempt>" when a job is claimed.
    if sys.argv[1:]==['--wait']:sys.argv[1:]=sys.stdin.readline().split()
    with db.connect() as c:
        row=c.execute('SELECT * FROM jobs WHERE id=?',(sys.argv[1],)).fetchone()
    if not row: raise SystemExit('Missing job')
    if row['kind']=='agent_turn':
        if len(sys.argv)!=3:raise SystemExit('Assistant runner needs its claimed attempt')
        db.check_lease(row['id'],int(sys.argv[2]))
    execute(dict(row))
