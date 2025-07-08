#!/bin/bash
cd weather_agent
timeout 60 python chatbot.py --multi-turn-demo 2>&1 | tee ../multi_turn_output.log
echo "Exit code: $?"