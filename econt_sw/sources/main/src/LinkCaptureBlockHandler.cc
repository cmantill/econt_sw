#include "LinkCaptureBlockHandler.h"
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>

#include <iostream>
#include <algorithm>
#include <stdio.h>

LinkCaptureBlockHandler::LinkCaptureBlockHandler(uhal::HwInterface* uhalHW,
						 std::string link_capture_block_name,
						 std::string bram_name,
						 std::vector<std::string> & elinks): m_uhalHW(uhalHW),
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
    data = std::vector<uint32_t>(size,0);

  char buf[200];
  sprintf(buf,"%s.%s",m_bram_name.c_str(),elink.c_str());
  uhal::ValVector<uint32_t> vec=m_uhalHW->getNode(buf).readBlock(size);
  m_uhalHW->dispatch();
  std::copy( vec.begin(), vec.end(), data.begin() );
   
}
