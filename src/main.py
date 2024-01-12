from fastapi import FastAPI, HTTPException, Request
import uvicorn
import grpc

from replicated_log_pb2_grpc import ReplicatedLogStub
from replicated_log_pb2 import Message
import threading
import argparse


import time

app = FastAPI()
LOGS = []
SECONDARIES = []
APPEND_COUNTER = 0
IS_TIMEOUT = 0


def replicate(secondary, message, counter):
    channel = grpc.insecure_channel(secondary)
    client = ReplicatedLogStub(channel)

    request = Message(message=message, counter=counter)
    
    try:
        response = client.LogMessage(request)
    except:
        return False

    print(f"{secondary} sent {response.ACK} as response")

    return response.ACK


@app.post("/add")
def add_log(message: str, write_concern: int):
    
    global IS_TIMEOUT
    global APPEND_COUNTER

    def replicate_with_message(condition, secondary, added_logs):
        global IS_TIMEOUT
        delay = 1
        while not replicate(secondary, message, APPEND_COUNTER):
            print(f'Going to sleep for {delay} seconds before another retry')
            time.sleep(delay)
            delay *= 2

            if delay == 2:
                IS_TIMEOUT = 1
                with condition:
                    condition.notify()

        added_logs.append(secondary)
        with condition:
            condition.notify()


    if write_concern > (len(SECONDARIES) + 1):
        raise HTTPException(status_code=400, detail="write_concern param can't be greater than number of secondaries + 1")
    
    IS_TIMEOUT = 0
    APPEND_COUNTER += 1
    LOGS.append({'message':message, 'counter': APPEND_COUNTER})

    added_logs = []

    condition = threading.Condition()

    for secondary in SECONDARIES:
        worker = threading.Thread(target=replicate_with_message, args=(condition, secondary, added_logs))
        worker.start()

    with condition:
        condition.wait_for(lambda: (len(added_logs)+1) >= write_concern or IS_TIMEOUT == 1)

    if (len(added_logs)+1) < write_concern and IS_TIMEOUT == 1:
        raise HTTPException(status_code=400, detail="Couldn't write log to required number of secondaries")

    return f'Message replicated to {len(added_logs)} secondaries'


@app.get("/logs")
def get_logs():
    return [elem['message'] for elem in sorted(LOGS, key=lambda v: v['counter'])]


@app.get("/secondary_startup")
def secondary_startup(port, request: Request):
    print(request.client)
    for log in LOGS:
        replicate(f'{request.client.host}:{port}', log['message'], log['counter'])



def start_fastapi_server(port):
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fastapi-port", type=int, dest="fastapi-port", required=True)
    parser.add_argument("-s", "--secondaries", nargs='+', type=str, dest="secondaries", required=True)
    args = vars(parser.parse_args())

    SECONDARIES = args['secondaries']

    start_fastapi_server(args['fastapi-port'])