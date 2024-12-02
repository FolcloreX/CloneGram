import asyncio
import time

class TokenBucket:
    """
    A class that implements the Token Bucket algorithm for rate-limiting.

    This class is used to manage the availability of tokens over time. The tokens can be consumed up to a
    specified limit (`max_tokens`), and they are refilled at a regular interval (`refill_interval`).

    Attributes:
        max_tokens (int): The maximum number of tokens that can be stored in the bucket.
        refill_interval (float): The time interval (in seconds) at which tokens are refilled.
        tokens (int): The current number of tokens in the bucket.
        last_refill_time (float): The timestamp of the last token refill.
    """

    def __init__(self, inicial_tokens: int, max_tokens: int, refill_interval: float):
        """
        Initializes the TokenBucket instance.

        Parameters:
            max_tokens (int): The maximum number of tokens that the bucket can hold.
            refill_interval (float): The interval (in seconds) between refills of the tokens.
        """
        self.max_tokens = max_tokens
        self.refill_interval = refill_interval
        self.tokens = inicial_tokens
        self.last_refill_time = time.time()

    def _refill_tokens(self):
        """
        Refills the token bucket based on the elapsed time since the last refill.

        The number of tokens added is calculated based on the time that has passed since the last refill. 
        Tokens are added in integer amounts, and the total number of tokens cannot exceed the maximum allowed 
        (`max_tokens`).

        This method is called before consuming tokens to ensure that the bucket has the appropriate number of tokens.
        """
        now = time.time()
        elapsed = now - self.last_refill_time
        refill_tokens = int(elapsed / self.refill_interval)
        
        if refill_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + refill_tokens)
            self.last_refill_time += refill_tokens * self.refill_interval

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempts to consume a specified number of tokens from the bucket.

        This method first refills the token bucket based on the elapsed time, then attempts to consume the 
        requested number of tokens. If there are enough tokens available, it subtracts them and returns `True`. 
        If not, it returns `False`.

        Parameters:
            tokens (int): The number of tokens to consume. Default is 1.

        Returns:
            bool: True if the tokens were successfully consumed, False otherwise.
        """
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
    bucket = TokenBucket(inicial_tokens=0, max_tokens=20, refill_interval=3)  # 20 messages per minute

    # Example: Sending 25 messages
    for i in range(25):
        await send_message(bucket, f"Message {i+1}")

if __name__ == "__main__":
    asyncio.run(main())

