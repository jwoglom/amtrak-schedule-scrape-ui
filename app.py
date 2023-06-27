#!/usr/bin/env python3

from flask import Flask, Response, request, abort, render_template, jsonify, send_from_directory
import os
import json
import subprocess

from analyze import parse_folder
from postprocess import postprocess_file

ROUTE_TOKEN = ''
static_url_path = '/static'
if os.getenv('ROUTE_TOKEN'):
    ROUTE_TOKEN = '/' + os.getenv('ROUTE_TOKEN')
    static_url_path = ROUTE_TOKEN + '/static'

app = Flask(__name__, static_folder='static', static_url_path = static_url_path)

DATA_FOLDER = 'data'
if os.getenv('DATA_FOLDER'):
    DATA_FOLDER = os.getenv('DATA_FOLDER')

ANALYZED_FOLDER = 'analyzed'
if os.getenv('ANALYZED_FOLDER'):
    ANALYZED_FOLDER = os.getenv('ANALYZED_FOLDER')

# Log messages with Gunicorn
if not app.debug:
    import logging
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.INFO)


@app.route(ROUTE_TOKEN + '/')
def index_route():
    return render_template('index.html', **{
        'route': request.args.get('route'),
        'date': request.args.get('date')
    })

@app.route(ROUTE_TOKEN + '/data/<path:path>')
def data_route(path):
    return send_from_directory(DATA_FOLDER, path)

@app.route(ROUTE_TOKEN + '/processed/<path:path>')
def processed_route(path):
    f = check_path(path)
    
    if os.path.isdir(f):
        print('processing directory', f)
        output = {}
        for file in os.listdir(f):
            if not file.endswith('.json'):
                continue
            out = postprocess_file(os.path.join(f, file))
            jout = None
            try:
                jout = json.loads(out)
            except Exception:
                pass
            output[file.split('/')[-1].split('.')[0]] = jout
        
        return jsonify(output)

    print('processing file', f)
    return postprocess_file(f)


@app.route(ROUTE_TOKEN + '/analyzed/<path>/<date>')
def analyzed_route(path, date):
    f = check_path(path)
    df = check_path(os.path.join(path, date))
    
    def parse_vararg(n):
        arg = request.args.get(n)
        if arg:
            arg = arg.split(',')
        else:
            arg = None
        return arg

    no_cache = request.args.get('no_cache') == 'true'
    if not no_cache:
        cf = check_analyzed_path(path)
        if cf:
            dcf = check_analyzed_path(os.path.join(path, '%s.json' % date), dircheck=False)
            if dcf:
                print('analyze (cached):', dcf, date)
                return jsonify(json.loads(open(dcf, 'r').read()))
    
    filter_snapshots = parse_vararg('filter_snapshots')
    with_detail = request.args.get('with_detail') == 'true'
    with_prices = request.args.get('with_prices', 'true') == 'true'
    
    print('analyze:', f, date, filter_snapshots, with_detail)

    out = parse_folder(f, filter_dates=[date], filter_snapshots=filter_snapshots, with_detail=with_detail, with_prices=with_prices)
    return jsonify(out)

@app.route(ROUTE_TOKEN + '/routes')
def get_routes_route():
    routes = []
    for file in os.listdir(DATA_FOLDER):
        if '-' in file and os.path.isdir(os.path.join(DATA_FOLDER, file)):
            routes.append(file)
    return jsonify(routes)

@app.route(ROUTE_TOKEN + '/routes/<route>')
def get_dates_route(route):
    f = check_path(route)
    days = {}
    for file in os.listdir(f):
        p = os.path.join(f, file)
        if os.path.isdir(p):
            scrapes = list(filter(lambda x: x.endswith('.json'), os.listdir(p)))
            days[file] = len(scrapes)
    return jsonify(days)

def check_path(path):
    f = os.path.normpath(os.path.join(DATA_FOLDER, path))
    if '..' in f or not f.startswith(os.path.normpath(DATA_FOLDER)):
        return abort(400, 'invalid path')
    
    if not os.path.exists(f):
        return abort(404, 'invalid path')
    
    if not os.path.isdir(f):
        return abort(400, 'invalid path')
    
    return f

def check_analyzed_path(path, dircheck=True):
    f = os.path.normpath(os.path.join(ANALYZED_FOLDER, path))
    if '..' in f or not f.startswith(os.path.normpath(ANALYZED_FOLDER)):
        return False

    if not os.path.exists(f):
        return False

    if dircheck and not os.path.isdir(f):
        return False

    return f

