from motor.motor_asyncio import AsyncIOMotorClient


class Mongo:
    client: AsyncIOMotorClient | None = None


async def connect_to_mongo(uri: str, db_name: str, app):
    Mongo.client = AsyncIOMotorClient(uri)
    app.mongodb = Mongo.client[db_name]


async def close_mongo():
    if Mongo.client:
        Mongo.client.close()
