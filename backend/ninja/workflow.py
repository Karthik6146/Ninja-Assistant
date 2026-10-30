from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
from .config import DATA

class State(TypedDict, total=False):
    project: str
    stage: str
    revision: int
    reviewed_revision: int

def open_graph():
    # Caller owns the context so SQLite connections are not leaked.
    return SqliteSaver.from_conn_string(str(DATA / 'checkpoints.sqlite'))

def graph(saver):
    def route(state): return {'stage':'waiting_review'}
    def review(state):
        answer=interrupt({'project':state['project'],'revision':state['revision'],'action':'Review captions and clip ranges'})
        if answer.get('revision')!=state['revision']: raise ValueError('Stale review')
        return {'stage':'reviewed','reviewed_revision':state['revision']}
    g=StateGraph(State); g.add_node('route',route); g.add_node('review',review)
    g.add_edge(START,'route'); g.add_edge('route','review'); g.add_edge('review',END)
    return g.compile(checkpointer=saver)

def begin(project,revision):
    with open_graph() as saver:
        return graph(saver).invoke({'project':project,'revision':revision},config={'configurable':{'thread_id':project+':'+str(revision)}})

def resume(project,revision):
    with open_graph() as saver:
        compiled=graph(saver)
        config={'configurable':{'thread_id':project+':'+str(revision)}}
        state=compiled.get_state(config)
        if not state.values or state.values.get('revision')!=revision:
            raise ValueError('Review checkpoint absent or stale')
        return compiled.invoke(Command(resume={'revision':revision}),config=config)
