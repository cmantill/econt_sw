#include "LinkCaptureBlockHandler.h"
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>

#include <iostream>
#include <algorithm>
#include <stdio.h>

LinkCaptureBlockHandler::LinkCaptureBlockHandler(uhal::HwInterface* uhalHW,
						 std::string link_capture_block_name): m_uhalHW(uhalHW),
										       m_link_capture_block_name(link_capture_block_name)
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
