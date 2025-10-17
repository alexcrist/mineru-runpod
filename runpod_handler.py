import time

import runpod


def handler(event):
    print("Worker start")
    input = event["input"]

    prompt = input.get("prompt")
    seconds = input.get("seconds", 0)

    print(f"Received prompt: {prompt}")
    print(f"Sleeping for {seconds} seconds...")

    # You can replace this sleep call with your own Python code
    time.sleep(seconds)

    return prompt


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
