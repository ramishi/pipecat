import asyncio
import os

import aiohttp

from dailyai.queue_frame import EndStreamQueueFrame, LLMMessagesQueueFrame
from dailyai.services.daily_transport_service import DailyTransportService
from dailyai.services.azure_ai_services import AzureLLMService, AzureTTSService
from dailyai.services.elevenlabs_ai_service import ElevenLabsTTSService
from dailyai.services.deepgram_ai_services import DeepgramTTSService
from dailyai.services.open_ai_services import OpenAILLMService
from examples.foundational.support.runner import configure


async def main(room_url):
    async with aiohttp.ClientSession() as session:
        meeting_duration_minutes = 1
        transport = DailyTransportService(
            room_url,
            None,
            "Say One Thing From an LLM",
            duration_minutes=meeting_duration_minutes,
            mic_enabled=True
        )

        llm = AzureLLMService(
            source_queue=asyncio.Queue(),
            api_key=os.getenv("AZURE_CHATGPT_API_KEY"),
            endpoint=os.getenv("AZURE_CHATGPT_ENDPOINT"),
            model=os.getenv("AZURE_CHATGPT_MODEL"),
        )

        tts = ElevenLabsTTSService(

            source_queue=llm.sink_queue,  # this should really be a sentence aggregator?
            aiohttp_session=session,
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
        )

        tts.sink_queue = transport.send_queue

        @transport.event_handler("on_first_other_participant_joined")
        async def on_first_other_participant_joined(transport, participant):
            messages = [{
                "role": "system",
                "content": "You are an LLM in a WebRTC session, and this is a 'hello world' demo. Say hello to the world."
            }]
            await llm.source_queue.put(LLMMessagesQueueFrame(messages))
            await llm.source_queue.put(EndStreamQueueFrame())
            # todo: commented out because it exits before audio plays
            # await transport.stop_when_done()

        await asyncio.gather(transport.run(), llm.process_queue(), tts.process_queue())


if __name__ == "__main__":
    (url, token) = configure()
    asyncio.run(main(url))
