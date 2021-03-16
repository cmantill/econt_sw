#include "eLinkOutputsBlockHandler.h"

#include <iostream>
#include <algorithm>
#include <stdio.h>

eLinkOutputsBlockHandler::eLinkOutputsBlockHandler(uhal::HwInterface* uhalHW,
						   std::string eLink_outputs_switch_name,
						   std::string eLink_outputs_stream_name) : m_switch_block_name(eLink_outputs_switch_name),
											    m_stream_block_name(eLink_outputs_stream_name)
{
}

void eLinkOutputsBlockHandler::setSwitchRegister(std::string elink, std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_switch_block_name.c_str(),elink.c_str(),regName.c_str());
  std::cout << "reg " << buf << " val " << value << std::endl;
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}

void eLinkOutputsBlockHandler::setStreamRegister(std::string elink, std::string regName, uint32_t value)
{
  char buf[200];
  sprintf(buf,"%s.%s.%s",m_stream_block_name.c_str(),elink.c_str(),regName.c_str());
  m_uhalHW->getNode(buf).write(value);
  m_uhalHW->dispatch();
}
