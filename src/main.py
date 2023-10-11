from fastapi import FastAPI
import uvicorn
import grpc

from replicated_log_pb2_grpc import ReplicatedLogStub
from replicated_log_pb2 import Message
from concurrent.futures import ThreadPoolExecutor
import argparse

app = FastAPI()
LOGS = []
SECONDARIES = []


def replicate(secondary, message):
    channel = grpc.insecure_channel(secondary)
    client = ReplicatedLogStub(channel)

    request = Message(message=message)
    response = client.LogMessage(request)

    print(f"{secondary} sent {response.ACK} as response")

    return response.ACK


@app.post("/add")
def add_log(message: str):
    LOGS.append(message)

    def replicate_with_message(secondary):
        replicate(secondary, message)
    

    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(replicate_with_message, SECONDARIES))

    return f'Message replicated to {len(responses)} secondaries'


@app.get("/logs")
def get_logs():
    return LOGS


def start_fastapi_server(port):
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fastapi-port", type=int, dest="fastapi-port", required=True)
    parser.add_argument("-s", "--secondaries", nargs='+', type=str, dest="secondaries", required=True)
    args = vars(parser.parse_args())

    SECONDARIES = args['secondaries']

    start_fastapi_server(args['fastapi-port'])