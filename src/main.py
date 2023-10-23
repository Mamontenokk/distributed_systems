from fastapi import FastAPI, HTTPException
import uvicorn
import grpc

from replicated_log_pb2_grpc import ReplicatedLogStub
from replicated_log_pb2 import Message
from concurrent.futures import ThreadPoolExecutor
import argparse

app = FastAPI()
LOGS = []
SECONDARIES = []
APPEND_COUNTER = 0


def replicate(secondary, message, counter):
    channel = grpc.insecure_channel(secondary)
    client = ReplicatedLogStub(channel)

    request = Message(message=message, counter=counter)
    response = client.LogMessage(request)

    print(f"{secondary} sent {response.ACK} as response")

    return response.ACK


@app.post("/add")
def add_log(message: str, write_concern: int):
    global APPEND_COUNTER

    if write_concern > (len(SECONDARIES) + 1):
        raise HTTPException(status_code=400, detail="write_concern param can't be greater than number of secondaries + 1")
    
    APPEND_COUNTER += 1
    LOGS.append({'message':message, 'counter': APPEND_COUNTER})

    def replicate_with_message(secondary):
        replicate(secondary, message, APPEND_COUNTER)


    executor = ThreadPoolExecutor(max_workers=5)
    futures = []

    for secondary in SECONDARIES:
        futures.append(executor.submit(replicate_with_message,secondary))

    while True:
        received_acks = sum([1 for future in futures if future.done()]) + 1 # +1 because log already present in main log
        if received_acks >= write_concern:
            return f'Message replicated to {received_acks} secondaries'

    


@app.get("/logs")
def get_logs():
    return [elem['message'] for elem in sorted(LOGS, key=lambda v: v['counter'])]


def start_fastapi_server(port):
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fastapi-port", type=int, dest="fastapi-port", required=True)
    parser.add_argument("-s", "--secondaries", nargs='+', type=str, dest="secondaries", required=True)
    args = vars(parser.parse_args())

    SECONDARIES = args['secondaries']

    start_fastapi_server(args['fastapi-port'])