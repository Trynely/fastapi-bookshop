from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider
from app.agents.container import AgentProvider
from app.product.container import product_providers
from app.shared.container import shared_providers
from app.support.container import support_providers
from app.client.container import ClientProvider

def create_dishka_container():
    return make_async_container(
        *shared_providers,
        *product_providers,
        *support_providers,
        ClientProvider(),
        AgentProvider(),
        FastapiProvider(),
    )