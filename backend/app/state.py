from litestar.datastructures.state import State as BaseState
from motor import motor_asyncio


class State(BaseState):
    mongo: motor_asyncio.AsyncIOMotorCollection
