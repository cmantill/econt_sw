#include "LinkCaptureBlockHandler.h"
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>

#include <iostream>
#include <algorithm>
#include <stdio.h>

LinkCaptureBlockHandler::LinkCaptureBlockHandler(uhal::HwInterface* uhalHW,
						 std::string link_capture_block_name, 
						 std::string bram_name, 
						 std::vector< link_description> & elinks) : m_uhalHW(uhalHW),
											    m_link_capture_block_name(link_capture_block_name),
											    m_bram_name(bram_name),
											    m_elinks(elinks)
{
}
