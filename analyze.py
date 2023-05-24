#!/usr/bin/env python3

import os
import json
import subprocess
from collections import OrderedDict
from datetime import datetime

from postprocess import postprocess_file

def process_snapshot(snapshot):
    ret = {}
    for train in snapshot:
        name = f'{train["trainName"]} {train["trainNumber"]}'
        fares = {}
        avail = {}
        for fare in train['fares']:
            farename = fare['class']+' '+fare['type']
            if farename in fares and float(fare['fare']) > fares[farename]:
                continue
            fares[farename] = float(fare['fare'])
            avail[farename] = fare['inventory']['available']

        ret[name] = {
            'fares': fares,
            'avail': avail,
            'sold': train['sold'],
            'start': train['originArrival'],
            'end': train['destArrival']
        }
    return ret
        
def parse_folder(data_folder, filter_dates=None, filter_snapshots=None, with_detail=False, with_prices=True):
    #print(f'{data_folder=}')
    ret = {}
    for folder in os.listdir(data_folder):
        folder_path = os.path.join(data_folder, folder)
        if not os.path.isdir(folder_path):
            continue
        if filter_dates and folder not in filter_dates:
            continue
        #print(f'{folder_path=}')
        build = {}
        for file in os.listdir(folder_path):
            if not file.endswith(".json"):
                continue
            snaptime = file.split('.')[0]
            if filter_snapshots and snaptime not in filter_snapshots:
                continue
            file_path = os.path.join(folder_path, file)
            #print(f'snapshot: {file_path}')
            snapshot = json.loads(postprocess_file(file_path))
            processed = process_snapshot(snapshot)
            for train, detail in processed.items():
                if train not in build:
                    build[train] = []
                detail["time"] = snaptime
                build[train].append(detail)
        for train in build.keys():
            build[train] = {
                "detail": sorted(build[train], key=lambda x: x['time'])
            }

            def timeToInt(t):
                parts = t.split('-')
                day = int(parts[0])
                hr = int(parts[1][:2])
                mn = int(parts[1][2:])
                return mn + 60*hr + 24*60*day
            def dtToInt(n):
                return n.minute + 60*n.hour + (n.year*10000 + n.month*100 + n.day)*24*60


            prices = []
            minTimes = []
            lastTime = 0
            minForTime = 0
            for detail in build[train]['detail']:
                minPrice = min(detail['fares'].values()) if detail['fares'] else None
                item = [detail['time'], minPrice]
                if not item[1]:
                    continue
                elif minTimes and item[1] == minTimes[0][1]:
                    minTimes.append(item)
                    minForTime += timeToInt(item[0]) - timeToInt(lastTime)
                elif minTimes and minTimes[0][1] and item[1] < minTimes[0][1]:
                    minTimes = [item]
                    minForTime = 0
                elif not minTimes:
                    minTimes = [item]
                    minForTime = 0
                prices.append(item)
                lastTime = item[0]

            pricesOnly = [i[1] for i in prices]

            curPriceFor = 0
            for i in range(len(prices)-1,0,-1):
                if prices[i][1] == prices[i-1][1]:
                    curPriceFor += timeToInt(prices[i][0]) - timeToInt(prices[i-1][0])
                else:
                    break

            if with_prices:
                build[train]['prices'] = prices
            def timeLabel(mins):
                ret = ''
                if mins//(60*24) > 0:
                    ret += f'{mins//(60*24)}d'
                if (mins//60)%24 > 0:
                    ret += f'{(mins//60)%24}h'
                if mins%60 > 0 and not (mins//60)>=24:
                    ret += f'{mins%60}m'
                return ret

            startDt = datetime.strptime(build[train]['detail'][0]['start'],  "%Y-%m-%dT%H:%M:%S")

            build[train]['curPrice'] = prices[-1][1] if prices else None
            build[train]['curPriceForMins'] = curPriceFor
            build[train]['curPriceFor'] = timeLabel(curPriceFor)
            build[train]['curPriceAt'] = timeLabel(dtToInt(startDt) - timeToInt(prices[-1][0])) if prices else None
            build[train]['minPrice'] = minTimes[0][1] if len(minTimes) > 0 else None
            build[train]['minTimes'] = [i[0] for i in minTimes]
            build[train]['minPriceForMins'] = minForTime
            build[train]['minPriceFor'] = timeLabel(minForTime)
            build[train]['minPriceAt'] = timeLabel(dtToInt(startDt) - timeToInt(minTimes[-1][0])) if prices else None
            build[train]['modePrice'] = max(set(pricesOnly), key=pricesOnly.count) if pricesOnly else None
            build[train]['meanPrice'] = (sum(pricesOnly) / len(pricesOnly)) if pricesOnly else None
            build[train]['start'] = build[train]['detail'][0]['start']
            build[train]['end'] = build[train]['detail'][0]['end']
            if not with_detail:
                del build[train]['detail']
        ret[folder] = build
    return ret

if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument('--folder', default=None)
    a.add_argument('--date', default=None)
    a.add_argument('--snapshot', default=None)
    a.add_argument('--with-detail', default=False, action='store_true')
    args = a.parse_args()
    out = parse_folder(args.folder, [args.date] if args.date else None, [args.snapshot] if args.snapshot else None, with_detail=args.with_detail)
    print(json.dumps(out))
