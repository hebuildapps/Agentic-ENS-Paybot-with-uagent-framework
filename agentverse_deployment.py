import os
from uagents_core.utils.registration import (
    register_chat_agent,
    RegistrationRequestCredentials,
)

register_chat_agent(
    "MeTTaPay",
    "https://agentic-ens-paybot-with-uagent-framework.onrender.com",
    active=True,
    credentials=RegistrationRequestCredentials(
        agentverse_api_key="eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjE3NTg5OTMxMTMsImlhdCI6MTc1ODk4OTUxMywiaXNzIjoiZmV0Y2guYWkiLCJqdGkiOiJlZjM4OGU5YzcwYThiMDdkNmI2MzE0NTQiLCJzY29wZSI6IiIsInN1YiI6IjZiZWMzMzA0MjU0M2JkYTJiZTNmMWYxNjZmODE5OTkzZTY5ZWIwZjk1ODBlMjJjZiJ9.C2Rto9rW8Yi0Nm5YcUvBOYHVRkUt_Jr0tdPes0peD_w2ct5XG3ZZqH96yOLuu5JKf9CLcYx91J4xyrPFF3J9AnbvL7gdBV_mqncPHbJT2A4hU0ZwlxTL8NBCWdPEIwlwQ_Yiym3pyhRguh89P6LGB08NNz77P5kmD5dzSHjRDVhDJdG_5i1NybCclntZpqBomZq223rsQM6EdR0FdqvQJTIrBLYgGQ1v4MaFhAXom-zooNfYvaQXTBSbix3wT0SAigywzdzWBOWJjQ60_xc58UiCPp-YYQT4x04EefB8y3bP5BpZU4L4zpH8rz2dAmBFTWUf9AolEOXyJNYWGuz6Iw",
        agent_seed_phrase="adult absorb acid always among actor about agree aerobic alcohol air ahead"
    ),
)