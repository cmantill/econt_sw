#include "LinkCaptureBlockHandler.h"
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>

#include <iostream>
#include <algorithm>
#include <stdio.h>

LinkCaptureBlockHandler::LinkCaptureBlockHandler(uhal::HwInterface* uhalHW,
						 std::string link_capture_block_name,
						 std::string bram_name,
						 std::vector<link_description> & elinks): m_uhalHW(uhalHW),
											  m_link_capture_block_name(link_capture_block_name),
											  m_bram_name(bram_name),
											  m_elinks(elinks)
{
}

void LinkCaptureBlockHandler::setRegister(std::string elink,std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_link_capture_block_name.c_str(),elink.c_str(),regName.c_str());
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}
void LinkCaptureBlockHandler::setRegister(std::string regName, uint32_t value)
{
  char buf[200];
  for( auto elink : m_elinks ){
    sprintf(buf,"%s.%s.%s",m_link_capture_block_name.c_str(),elink.name().c_str(),regName.c_str());
    m_uhalHW->getNode(buf).write(value);
  }
  m_uhalHW->dispatch();
}

void LinkCaptureBlockHandler::setGlobalRegister(std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_link_capture_block_name.c_str(),"global",regName.c_str());
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}

const uint32_t LinkCaptureBlockHandler::getRegister(std::string elink, std::string regName)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_link_capture_block_name.c_str(),elink.c_str(),regName.c_str());
  uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
  m_uhalHW->dispatch();
  return (uint32_t)val;
}

const uint32_t LinkCaptureBlockHandler::getGlobalRegister(std::string regName)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_link_capture_block_name.c_str(),"global",regName.c_str());
  uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
  m_uhalHW->dispatch();
  return (uint32_t)val;
}

void LinkCaptureBlockHandler::getData(std::string elink, std::vector<uint32_t> &data, uint32_t size)
{
  if( data.size()!=size )
    data = std::vector<uint32_t>(size);
  char buf[200];
  sprintf(buf,"%s.%s",m_bram_name.c_str(),elink.c_str());
  uhal::ValVector<uint32_t> vec=m_uhalHW->getNode(buf).readBlock(size);
  m_uhalHW->dispatch();
  std::copy( vec.begin(), vec.end(), data.begin() );
}

/* Acquire
 * capture_mode: 
 * - 0 (inmediate)
 * - 1 (writes data starting on a specific BX count)
 * - 2 (L1A or fast command)
 * - 3 (auto daq mode)
 * fc:
 * - 0 (no fast command)
 * - 1 (L1A)
 * - 2 (linkreset_ECONt)
 * - 3 (linkreset_ECONd)
 * - 4 (linkreset_ROCt)
 * - 5 (linkreset_ROCd)
 *
 * e.g. for linkreset_ECONt: acquire(2,2), for acquire(2,4)
 */
void LinkCaptureBlockHandler::acquire(int capture_mode, int fc, int nwords=4095, int bx=0)
{
  for( auto elink : m_elinks ){
    // set the BX offset of all 13 links
    setRegister(elink.name(),"L1A_offset_or_BX",bx);
    
    // set the capture mode
    setRegister(elink.name(),"capture_mode_in",capture_mode); // 2 (Link-reset), 1 (manual)
    setRegister(elink.name(),"capture_L1A",0);
    setRegister(elink.name(),"capture_linkreset_ECONt",0);
    setRegister(elink.name(),"capture_linkreset_ECONd",0);
    setRegister(elink.name(),"capture_linkreset_ROCt",0);
    setRegister(elink.name(),"capture_linkreset_ROCd",0);

    // set the acquire length of all 13 links                                                                                                                                                             
    setRegister(elink.name(),"aquire_length",nwords);

    // set to acquire
    setRegister(elink.name(),"aquire",1);
  }
}

/* Get captured data
 */
bool LinkCaptureBlockHandler::getCapturedData( std::vector< std::vector<uint32_t> > &linksdata, int noutputlinks, int nwords=4095)
{
  // check that fifos have the same occupancy
  while(1){
    std::vector<int> fifo_occupancies;
    for( auto elink : m_elinks ){
      uint32_t fifo_occupancy = getRegister(elink.name(),"fifo_occupancy");
      fifo_occupancies.push_back( (int)fifo_occupancy);
    }
    if( (std::count(std::begin(fifo_occupancies), std::end(fifo_occupancies), fifo_occupancies.front()) == (int)fifo_occupancies.size()) && fifo_occupancies.at(0)==nwords){
      std::cout << "All fifo occupancies are the same and " << nwords << std::endl;
      break;
    }
    else{
      std::cout << "FIFO not filled." << std::endl;
      return false;
    }
  }
  
  // get data
  int id=0;
  for( auto elink : m_elinks ){
    uint32_t fifo_occupancy =  getRegister(elink.name(),"fifo_occupancy");
    getData( elink.name(), linksdata[id], fifo_occupancy );
    id++;
  }
  return true;
}
