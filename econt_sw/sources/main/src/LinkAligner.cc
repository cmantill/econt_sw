#include <LinkAligner.h>

#include <iostream>
#include <sstream>
#include <fstream>
#include <cstring>
#include <iomanip>
#include <algorithm>

LinkAligner::LinkAligner(uhal::HwInterface* uhalHWInterface, 
			 FastControlManager* fc)
{
  m_uhalHW = uhalHWInterface;
  m_fcMan = fc;

  auto buildname = [](std::string base, int val)->std::string{ return base+std::to_string(val); };

  // setting up the eLink output to send the link reset pattern and stream one complete orbit from RAM
  eLinkOutputsBlockHandler out( m_uhalHW,
				std::string("eLink_outputs_ipif_switch_mux"),
				std::string("eLink_outputs_ipif_stream_mux")
				);

  std::vector<std::string> eLinks;
  auto base = std::string("link");
  for( int i=0; i<12; i++ ){
    std::string name=buildname(base,i);
    eLinks.push_back(name);
  }

  for(auto eLink : eLinks){
    // Select the stream from RAM as the source
    out.setSwitchRegister(eLink,"output_select",0);
  }
    /*
    // Send 255 words in the link reset pattern
    out.setSwitchRegister(eLink,"n_idle_words",255);
    // Send this word for almost all of the link reset pattern
    out.setSwitchRegister(eLink,"idle_word",0xaccccccc);
    // Send this word on BX0 during the link reset pattern
    out.setSwitchRegister(eLink,"idle_word_BX0",0x9ccccccc);
  }

  for(auto eLink : eLinks){
    // Stream one complete orbit from RAM before looping
    out.setStreamRegister(eLink,"sync_mode",1);
    // Determine pattern length in orbits: 1
    out.setStreamRegister(eLink,"ram_range",1);
  }
  */

  // let's make sure the FC is ready for link alignment procedure
  for( int i=0; i<3; i++ ){
    m_fcMan->resetFC(); // send a link reset
    m_fcMan->clear_ink_reset_l1a(); // clear the link reset and L1A request bits
    std::cout << "enable_FC_stream " << m_fcMan->getRegister("command.enable_fast_ctrl_stream") << std::endl;
    std::cout << "orbit sync " << m_fcMan->getRegister("command.enable_orbit_sync") << std::endl;
    // maybe we can't read link reset because it is write only?
    std::cout << "link reset " << m_fcMan->getRegister("command.link_reset") << std::endl;
  }


  // sending a link reset and L1A together, to capture the reset sequence
  // set the BX on which link reset will be sent
  m_fcMan->set_link_reset_bx(3550); // sync pattern from eLink_outputs appears in the snapshot 2 BX later? 
  m_fcMan->set_l1a_A_bx(3549); // BX on which L1A will be sent
  // send a link reset fast command and an L1A 
  m_fcMan->send_link_reset_l1a(); 
  // clear the link reset and L1A request bits
  m_fcMan->clear_ink_reset_l1a();


}
