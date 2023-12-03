from concurrent import futures
import logging

import grpc
from replicated_log_pb2_grpc import add_ReplicatedLogServicer_to_server, ReplicatedLogServicer
from replicated_log_pb2 import MessageACK
import threading
import argparse
import requests

#for testing purposes only
import time
from random import randint

from fastapi import FastAPI
import uvicorn

app = FastAPI()

LOGS = []
TERMINATE_FLAG = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


class Logger(ReplicatedLogServicer):
    def LogMessage(self, request, context):
        append_data = {'message': request.message, 'counter': request.counter}
        
        if append_data in LOGS:
            logging.info('Log already present')
            return MessageACK(ACK=True) #True because message is already replicated => task is done
        
        else:
            sleep_duration = randint(1, 10)
            logging.info(f"going to sleep for {sleep_duration} seconds")
            time.sleep(sleep_duration)
            logging.info(f"Adding {request.message} to logs")
            LOGS.append(append_data)
            return MessageACK(ACK=True)
    

def start_grpc_server(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_ReplicatedLogServicer_to_server(Logger(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()

    logging.info("Server started, listening on " + port)

    while not TERMINATE_FLAG:
        pass

    logging.info("Stopping gRPC server")

    server.stop(0)


@app.get("/logs")
def get_logs():
    response = []

    for log, i in zip(sorted(LOGS, key=lambda v: v['counter']), range(1,len(LOGS)+1)):
        if log['counter'] == i:
            response.append(log['message'])

    return response


def start_fastapi_server(port):
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--grpc-port", type=str, dest="grpc-port", required=True)
    parser.add_argument("-f", "--fastapi-port", type=int, dest="fastapi-port", required=True)
    parser.add_argument("-m", "--main-server", type=str, dest="main-server", required=True)
    args = vars(parser.parse_args())

    grpc_thread = threading.Thread(target=start_grpc_server, args=(args["grpc-port"],))
    grpc_thread.start()

    try:
        requests.get(f"http://{args['main-server']}/secondary_startup?port={args['grpc-port']}")
    except:
        logging.info('Error while trying to send request to the main server')

    start_fastapi_server(args['fastapi-port'])

    TERMINATE_FLAG = True
    grpc_thread.join()
