import asyncio
import time

class TokenBucket:
    def __init__(self, inicial_tokens: int, max_tokens: int, refill_interval: float):
        self.max_tokens = max_tokens
        self.refill_interval = refill_interval
        self.tokens = inicial_tokens
        self.last_refill_time = time.time()

    def _refill_tokens(self):
        now = time.time()
        elapsed = now - self.last_refill_time
        refill_tokens = int(elapsed / self.refill_interval)
        
        if refill_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + refill_tokens)
            self.last_refill_time += refill_tokens * self.refill_interval

    def consume(self, tokens: int = 1) -> bool:
        self._refill_tokens()

        # If we have enough tokens to subtract
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

# Just in case I want to implement tests =)
async def send_message(bucket: TokenBucket, message: str):
    while not bucket.consume():
        print("Rate limit reached. Waiting for tokens...")
        await asyncio.sleep(1)

    # Simulate sending the message
    print(f"Message sent: {message}")

async def main():
    # 20 Messages per minute
    bucket = TokenBucket(inicial_tokens=0, max_tokens=20, refill_interval=3)

    # Example: Sending 25 messages
    for i in range(25):
        await send_message(bucket, f"Message {i+1}")

if __name__ == "__main__":
    asyncio.run(main())

