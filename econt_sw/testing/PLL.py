import logging
logger = logging.getLogger("pll")
logger.setLevel(logging.INFO)

from utils.pll_lock_count import PLLLockCount

pll=PLLLockCount()

def get_count():
    logger.info('Loss of lock count %s'%pll.getCount())
    logger.info('Edge to count %s'%pll.edgeSel(read=True))
    pll.edgeSel(val=1)
    logger.info('Edge to count %s'%pll.edgeSel(read=True))
    pll.edgeSel(val=0)
    logger.info('Edge to count %s'%pll.edgeSel(read=True))
    logger.info('Loss of lock count %s'%pll.getCount())
    
    # reset counters
    pll.reset()
    
    logger.info('Loss of lock count %s'%pll.getCount())

if __name__=='__main__':
    get_count()
