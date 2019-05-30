#!/usr/bin/env node

var express = require('express');
var http = require('http');
var https = require('https');
var debug = require('debug')('permalight');
var fs     = require('fs');
var bodyParser = require('body-parser');
var basicAuth = require('express-basic-auth');
var helmet = require('helmet');
var mqtt  = require('mqtt');

var options = {
  cert: fs.readFileSync('/etc/letsencrypt/live/permalight.eecs.berkeley.edu/fullchain.pem'),
  key:  fs.readFileSync('/etc/letsencrypt/live/permalight.eecs.berkeley.edu/privkey.pem'),
};

var MQTT_TOPIC_NAME = 'permalight';

var mqtt_client = mqtt.connect('mqtt://localhost');
mqtt_client.on('connect', function () {
    debug('Connected to MQTT');

  var app = express();
  app.use(function(req, res, next) {
    if (req.secure) {
      return next();
    }
    debug('redirected');
    res.redirect(307, 'https://' + req.hostname + req.url);
  });
  app.use(helmet());
  app.use(basicAuth({users: { 'admin': 'password' }}));
  app.use(bodyParser.json());

  app.get('/health-check', (req, res) => res.sendStatus(200));
  app.post('/permalight', process_request);

  http.createServer(app).listen(80);
  https.createServer(options, app).listen(443);

});

process_request = function(req, res) {
  var light = req.body.light_name;
  debug('Light: ' + light);
  var action = req.body.action;
  debug('Action: ' + action);
  if (req.method == 'GET') {
    res.sendStatus(400);
    return;
  }
  else if (req.method == 'POST') {
    if (action === 'enable') {
      var value = parseInt(req.body.value, 10);
      debug('Value: ' + value);
      if (isNaN(value)) {
        res.status(400).send(JSON.stringify({ "result": "Invalid value for enable, must be an integer" }));
        return;
      }
      else if (!(value == 0 || value == 1)) {
        res.status(400).send(JSON.stringify({ "result": "Invalid value for enable, must be boolean" }));
        return;
      }
      value = Boolean(value);
      payload = {light_name: light, enable: value};
      mqtt_client.publish(MQTT_TOPIC_NAME + '/' + light, JSON.stringify(payload), {retain: true});
      res.status(200).send(JSON.stringify({ result: 'Success!' }));
      return;
    }
    else if (action === 'set_point') {
      var value = parseInt(req.body.value, 10);
      debug('Value: ' + value);
      if (isNaN(value)) {
        res.status(400).send(JSON.stringify({ "result": "Invalid value for set point, must be an integer" }));
        return;
      }
      else if (value < 0) {
        res.status(400).send(JSON.stringify({ "result": "Invalid value for set point, must be greater than 0" }));
        return;
      }
      payload = {light_name: light, set_point: value};
      mqtt_client.publish(MQTT_TOPIC_NAME + '/' + light, JSON.stringify(payload), {retain: true});
      res.status(200).send(JSON.stringify({ result: 'Success!' }));
      return;
    }
    else if (action === 'bright') {
      payload = {light_name: light, bright: 1};
      mqtt_client.publish(MQTT_TOPIC_NAME + '/' + light, JSON.stringify(payload), {retain: true});
      res.status(200).send(JSON.stringify({ result: 'Success!' }));
      return;
    }
    else if (action === 'dim') {
      payload = {light_name: light, dim: 1};
      mqtt_client.publish(MQTT_TOPIC_NAME + '/' + light, JSON.stringify(payload), {retain: true});
      res.status(200).send(JSON.stringify({ result: 'Success!' }));
      return;
    }
    else {
      res.sendStatus(400);
      return;
    }
  }
  else {
    res.sendStatus(400);
    return;
  }
};


