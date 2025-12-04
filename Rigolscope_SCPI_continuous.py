import os
import concurrent.futures
import numpy as np
import time
import matplotlib.pyplot as plt

from Rigolscope_SCPI import rigol_scpi, initialize_logger

def save_local_continuous(IP, cal_file, logger):
    """
    Continuously force trig the scope and save the data to the NAS
    192.168.140.229 : DIAG SCOPE 2
    192.168.140.230 : DIAG SCOPE 3
    """
    try:
        scope = rigol_scpi(IP)
        start = time.time()
        scope.run()
        time.sleep(0.2)
        scope.force_trig()
        
        scope.get_all_ch_waveform()
        scope.run()
        scope.write_waveform(cal_file)
        time_taken = time.time()-start
        print(f"Completed {IP} in {time_taken:.2f} seconds\n")
        logger.info(f"Completed {IP} in {time_taken:.2f} seconds\n")
        return time_taken
    except Exception as E:
        logger.error(f"Unable to complete {IP}")
        logger.error(E)
        return E
    
if __name__ == "__main__":
    try:
        os.remove("/home/whamdata/WHAM_Data/logs/rigol_scope.log")
    except:
        pass
    
    for n in range(0, 1000):
        processes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            for IP in ["192.168.140.230"]:
            #for IP in ["192.168.140.229", "192.168.140.230"]:
                logger = initialize_logger("/home/whamdata/WHAM_Data/logs/rigol_continuous.log", IP)
                cal_file = "/mnt/n/whamdata/x-ray_cal/SrBa133_CLCs137_2_251120/" + IP + "_" + str(n)
                processes.append(executor.submit(save_local_continuous, IP, cal_file, logger))
            for _ in concurrent.futures.as_completed(processes):
                print(f'Time taken for {IP} in iteration {n}: ', _.result())