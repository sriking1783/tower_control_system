import os
import json
import aio_pika
import asyncio
from aio_pika.abc import AbstractIncomingMessage
from typing import Callable, Awaitable

AMQP_URL = os.getenv("AMQP_URL", "amqp://guest:guest@atc_message_broker:5672/")

class ATCEventBroker:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.dlx_exchange = None
    
    async def connect(self):
        retry_interval = 2
        while True:
            try:
                # Robust connection auto-reconnects AFTER the initial link succeeds
                self.connection = await aio_pika.connect_robust(AMQP_URL)
                self.channel = await self.connection.channel()
                
                await self.channel.set_qos(prefetch_count=10)
                
                self.exchange = await self.channel.declare_exchange(
                    "atc.telemetry",
                    type=aio_pika.ExchangeType.TOPIC,
                    durable=True,
                )
                
                self.dlx_exchange = await self.channel.declare_exchange(
                    "atc.dlx",
                    type=aio_pika.ExchangeType.DIRECT,
                    durable=True,
                )
                
                dlq = await self.channel.declare_queue("atc.dead_letter_queue", durable=True)
                await dlq.bind(self.dlx_exchange, routing_key="poison_pill")
                
                print("Successfully connected to RabbitMQ and declared 'atc.telemetry' exchange.")
                break # Exit the loop once fully initialized
                
            except (OSError, aio_pika.exceptions.AMQPConnectionError):
                print(f"[BROKER] RabbitMQ port not ready yet. Retrying in {retry_interval}s...")
                await asyncio.sleep(retry_interval)
    
    async def publish_event(self, routing_key: str, payload: dict):
        if not self.exchange:
            raise RuntimeError("Broker is not connected. Call connect() first.")
        
        message_body = json.dumps(payload).encode()
        await self.exchange.publish(
            aio_pika.Message(
                body=message_body,
                content_type="application/json"
            ),
            routing_key=routing_key
        )
    
    async def start_consuming(self, queue_name: str, callback: Callable[[AbstractIncomingMessage], Awaitable[None]]):
        """
        Dynamically declares a queue, binds it to the topic exchange, 
        and starts listening for pushed events.
        """
        if not self.channel or not self.exchange:
            raise RuntimeError("Broker is not initialized. Call connect() first.")
        
        # Define under-the-hood argument flags telling RabbitMQ exactly what to do 
        # if a message expires due to TTL or gets explicitly rejected with requeue=False.
        queue_arguments = {
            "x-dead-letter-exchange": "atc.dlx",
            "x-dead-letter-routing-key": "poison_pill",
            "x-message-ttl": 45000  # 45-second fallback: drop to DLQ if worker grinds to a halt
        }
        
        # 1. Declare the persistent queue
        queue = await self.channel.declare_queue(queue_name, durable=True, arguments=queue_arguments)
        # 2. Match the routing pattern your spawner uses
        # If your spawner uses "atc.inbound.ingest", bind exactly to it.
        # If you want this queue to grab EVERYTHING, you could use "atc.#"
        routing_key = "atc.inbound.ingest"
        await queue.bind(self.exchange, routing_key=routing_key)
        print(f"[BROKER] Queue '{queue_name}' declared and bound to exchange with key '{routing_key}'")
        
        # 3. Start feeding the incoming consumer stream into your orchestrator handler callback
        await queue.consume(callback)
        print(f"[BROKER] Consumer fully active on queue: {queue_name}")
        

atc_broker = ATCEventBroker()
