#!/bin/bash

dir=$(dirname $0)
source $dir/slots.sh
source $dir/pwm.sh
source $dir/gpio.sh
source $dir/adc.sh

## Examples; These pins are not currently in use

## GPIO example - P8_35 (gpio8)
# load_gpio 8

## PWM example - P8_19 (pwm5/EHR2A)
# load_pwm     5 
# set_period   5 20000000
# set_duty     5 10000000 
# set_polarity 5 0
# run_pwm      5  

## ADC example
# enable_adcs
# load_slot BB-BONE-PRU-01
