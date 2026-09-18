#!/bin/bash
sudo -u postgres psql -d ffmotors_db -c "DELETE FROM motos WHERE placa = 'FF27MOT';"
