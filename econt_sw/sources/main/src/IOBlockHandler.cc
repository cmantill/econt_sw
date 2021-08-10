#include "IOBlockHandler.h"
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>

#include <iostream>
#include <algorithm>
#include <stdio.h>

IOBlockHandler::IOBlockHandler(uhal::HwInterface* uhalHW,
			       std::string IO_block_name,
			       std::vector<link_description> & elinks): m_uhalHW(uhalHW),
									m_IO_block_name(IO_block_name),
									m_elinks(elinks)
{
}

void IOBlockHandler::setRegister(std::string elink,std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_IO_block_name.c_str(),elink.c_str(),regName.c_str());
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}

void IOBlockHandler::setGlobalRegister(std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_IO_block_name.c_str(),"global",regName.c_str());
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}

const uint32_t IOBlockHandler::getRegister(std::string elink, std::string regName)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_IO_block_name.c_str(),elink.c_str(),regName.c_str());
  uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
  m_uhalHW->dispatch();
  return (uint32_t)val;
}

const uint32_t IOBlockHandler::getGlobalRegister(std::string regName)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_IO_block_name.c_str(),"global",regName.c_str());
  uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
  m_uhalHW->dispatch();
  return (uint32_t)val;
}
