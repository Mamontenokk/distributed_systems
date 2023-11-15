from fastapi import FastAPI, HTTPException
import uvicorn
import grpc

from replicated_log_pb2_grpc import ReplicatedLogStub
from replicated_log_pb2 import Message
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, Condition
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

    def replicate_with_message(condition, secondary, added_logs):
        replicate(secondary, message, APPEND_COUNTER)
        added_logs.append(secondary)
        with condition:
            condition.notify()

    if write_concern > (len(SECONDARIES) + 1):
        raise HTTPException(status_code=400, detail="write_concern param can't be greater than number of secondaries + 1")
    
    APPEND_COUNTER += 1
    LOGS.append({'message':message, 'counter': APPEND_COUNTER})

    added_logs = []

    condition = Condition()

    for secondary in SECONDARIES:
        worker = Thread(target=replicate_with_message, args=(condition, secondary, added_logs))
        worker.start()

    with condition:
        condition.wait_for(lambda: (len(added_logs)+1) >= write_concern)

    return f'Message replicated to {len(added_logs)} secondaries'


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