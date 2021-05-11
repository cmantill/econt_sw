#include "eLinkOutputsBlockHandler.h"
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>

#include <iostream>
#include <algorithm>
#include <stdio.h>

eLinkOutputsBlockHandler::eLinkOutputsBlockHandler(uhal::HwInterface* uhalHW,
						   std::string stream_block_name,
						   std::string switch_block_name,
						   std::vector<std::string> bram_names): m_uhalHW(uhalHW),
											 m_stream_block_name(stream_block_name),
											 m_switch_block_name(switch_block_name),
											 m_bram_names(bram_names)
{
}

void eLinkOutputsBlockHandler::setStreamRegister(std::string elink,std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_stream_block_name.c_str(),elink.c_str(),regName.c_str());
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}

void eLinkOutputsBlockHandler::setSwitchRegister(std::string elink,std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_switch_block_name.c_str(),elink.c_str(),regName.c_str());
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}

void eLinkOutputsBlockHandler::setData(std::string bram_name, std::vector<uint32_t> data, uint32_t size)
{
  if( data.size()!=size )
    return;
  m_uhalHW->getNode(bram_name).writeBlock(data);
  m_uhalHW->dispatch();
}
