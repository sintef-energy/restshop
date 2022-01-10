import matplotlib.pyplot as plt
import pandas as pd

# import requests
import sys, os
sys.path.append(os.getcwd())
from main import app

import uvicorn
from multiprocessing import Process
import contextlib
import threading
import time

from pyshop import ShopSession

proc = None
host = '127.0.0.1'
port = 8000

class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()

config = uvicorn.Config("main:app", host=host, port=port, log_level="info")
server = Server(config=config)

with server.run_in_thread():
    shop = ShopSession(host=host, port=port)

    # Set time resolution
    starttime = pd.Timestamp('2018-02-27')
    endtime = pd.Timestamp('2018-02-28')
    shop.set_time_resolution(starttime=starttime, endtime=endtime, timeunit='hour')

    # Add topology
    rsv1 = shop.model.reservoir.add_object('Reservoir1')
    rsv1.max_vol.set(12)
    rsv1.lrl.set(90)
    rsv1.hrl.set(100)
    rsv1.vol_head.set(pd.Series([90, 100, 101], index=[0, 12, 14], name=0))
    rsv1.flow_descr.set(pd.Series([0, 1000], index=[100, 101], name=0))

    plant1 = shop.model.plant.add_object('Plant1')
    plant1.outlet_line.set(40)
    plant1.main_loss.set([0.0002])
    plant1.penstock_loss.set([0.0001])

    p1g1 = shop.model.generator.add_object('Plant1_G1')
    plant1.connect_to(p1g1)
    p1g1.penstock.set(1)
    p1g1.p_min.set(25)
    p1g1.p_max.set(100)
    p1g1.p_nom.set(100)
    p1g1.startcost.set(500)
    p1g1.gen_eff_curve.set(pd.Series([95, 98], index=[0, 100]))
    p1g1.turb_eff_curves.set([pd.Series([80, 95, 90], index=[25, 90, 100], name=90),
                            pd.Series([82, 98, 92], index=[25, 90, 100], name=100)])

    rsv2 = shop.model.reservoir.add_object('Reservoir2')
    rsv2.max_vol.set(5)
    rsv2.lrl.set(40)
    rsv2.hrl.set(50)
    rsv2.vol_head.set(pd.Series([40, 50, 51], index=[0, 5, 6]))
    rsv2.flow_descr.set(pd.Series([0, 1000], index=[50, 51]))

    plant2 = shop.model.plant.add_object('Plant2')
    plant2.outlet_line.set(0)
    plant2.main_loss.set([0.0002])
    plant2.penstock_loss.set([0.0001])

    p2g1 = shop.model.generator.add_object('Plant2_G1')
    plant2.connect_to(p2g1)
    p2g1.penstock.set(1)
    p2g1.p_min.set(25)
    p2g1.p_max.set(100)
    p2g1.p_nom.set(100)
    p2g1.startcost.set(500)
    p2g1.gen_eff_curve.set(pd.Series([95, 98], index=[0, 100]))
    p2g1.turb_eff_curves.set([pd.Series([80, 95, 90], index=[25, 90, 100], name=90),
                            pd.Series([82, 98, 92], index=[25, 90, 100], name=100)])

    # Connect objects
    rsv1.connect_to(plant1)
    plant1.connect_to(rsv2)
    rsv2.connect_to(plant2)

    rsv1.start_head.set(92)
    rsv2.start_head.set(43)
    rsv1.energy_value_input.set(39.7)
    rsv2.energy_value_input.set(38.6)

    shop.model.market.add_object('Day_ahead')
    da = shop.model.market.Day_ahead
    da.sale_price.set(39.99)
    da.buy_price.set(40.01)
    da.max_buy.set(9999)
    da.max_sale.set(9999)

    rsv1.inflow.set(pd.DataFrame([101, 50], index=[starttime, starttime + pd.Timedelta(hours=1)]))

    shop.start_sim([], ['3'])
    shop.set_code(['incremental'], [])
    shop.start_sim([], ['3'])

    plt.title('Production and price')
    plt.xlabel('Time')
    plt.ylabel('Production [MW]')

    ax = shop.model.market.Day_ahead.sale_price.get().plot(legend='Price', secondary_y=True)
    shop.model.plant.Plant1.production.get().plot(legend='Plant 1')
    shop.model.plant.Plant2.production.get().plot(legend='Plant 2')
    ax.set_ylabel('Price [NOK]')
    plt.show()

    plt.figure(2)
    prod = shop.model.reservoir.Reservoir1.inflow.get()
    prod.plot()

    prod = shop.model.reservoir.Reservoir1.storage.get()
    prod.plot()

    prod = shop.model.reservoir.Reservoir2.storage.get()
    prod.plot()

    plt.show()