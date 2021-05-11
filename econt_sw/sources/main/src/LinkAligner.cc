#include <LinkAligner.h>

#include <iostream>
#include <sstream>
#include <fstream>
#include <cstring>
#include <iomanip>
#include <algorithm>
#include <chrono>
#include <thread>

#include <stdio.h>

LinkAligner::LinkAligner(uhal::HwInterface* uhalHWInterface, 
			 FastControlManager* fc)
{
  m_uhalHW = uhalHWInterface;
  m_fcMan = fc;

  auto buildname = [](std::string base, int val)->std::string{ return base+std::to_string(val); };
  auto base = std::string("link");

  // output links                                                                                                                                                            
  std::vector<std::string> elinksOutput;
  for( int i=0; i<NUM_OUTPUTLINKS; i++ ){
    std::string name=buildname(base,i);
    elinksOutput.push_back(name);
  }

  // link capture
  LinkCaptureBlockHandler lchandler( m_uhalHW,
                                     std::string("link_capture_axi"),
				     std::string("link_capture_axi_full_ipif"),
				     elinksOutput
				     );
  
  // fromIO
  IOBlockHandler fromIOhandler( m_uhalHW,
                                std::string("from_ECONT_IO_axi_to_ipif")
                                );
  m_lchandler = lchandler;
  m_fromIO = fromIOhandler;

}

void LinkAligner::align() {
  // sending 3 link resets to get IO delays set up properly
  m_fcMan->resetFC();
  for( int i=0; i<3; i++ ){
    m_fcMan->link_reset(0x1); 
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
    m_fcMan->clear_link_reset();
  }

  // reset and configure all links
  // enable all 13 links
  m_lchandler.setRegister("global","link_enable",0x1fff);
  // reset all links
  m_lchandler.setRegister("global","explicit_resetb",0x0);
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
  m_lchandler.setRegister("global","explicit_resetb",0x1);

  for(auto elink : m_lchandler.getElinks()){
    // set the alignment pattern for all links
    m_lchandler.setRegister(elink,"align_pattern",SYNC_WORD);
    // set the capture mode of all 13 links to 2 (L1A)
    m_lchandler.setRegister(elink,"capture_mode_in",2);
    // set the BX offset of all 13 links
    uint32_t bx_offset = m_lchandler.getRegister(elink,"L1A_offset_or_BX");
    m_lchandler.setRegister(elink,"L1A_offset_or_BX", (bx_offset&0xffff0000)|10 );
    // set the acquire length of all 13 links
    m_lchandler.setRegister(elink,"aquire_length", 256);
    // set the latency buffer based on the IO delays (1 or 0)
    uint32_t delay_out = m_fromIO.getRegister(elink,"delay_out");
    m_lchandler.setRegister(elink,"fifo_latency", 1*(delay_out<0x100));
    // tell link capture to do an acquisition
    m_lchandler.setRegister(elink,"aquire", 1);
  }

  // sending a link reset and L1A together, to capture the reset sequence
  // set the BX on which link reset will be sent (sync pattern from eLink_outputs appears in the snapshot 2 BX later)
  m_fcMan->set_link_reset_bx(3550); 
  // set the BX on which L1A will be sent
  m_fcMan->set_l1a_A_bx(3549); 
  // send a link reset fast command and an L1A 
  m_fcMan->link_reset(0x1);
  m_fcMan->l1a_A(0x1);
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
  // clear the link reset
  m_fcMan->clear_link_reset();
}

bool LinkAligner::checkLinks()
{
  // check alignment status
  for( auto elink : m_lchandler.getElinks() ){
    auto isaligned = m_lchandler.getRegister(elink,"status.link_aligned");
    if(!isaligned){
      std::cout << "Error :  " << elink << " is not aligned" << std::endl;
      return false;
    }
  }

  // check data integrity
  auto linksdata = std::vector< std::vector<uint32_t> >(NUM_OUTPUTLINKS);
  int id=0;
  std::vector<int> positions;
  for( auto elink : m_lchandler.getElinks() ){
    uint32_t fifo_occupancy =  m_lchandler.getRegister(elink,"fifo_occupancy");
    std::cout << "fifo link aligner " << fifo_occupancy<< std::endl;
    m_lchandler.getData( elink, linksdata[id], fifo_occupancy );
    int nBX0 = (int)std::count( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
    auto posit = std::find( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
    if (posit !=  linksdata[id].end()){
      positions.push_back(posit - linksdata[id].begin());
    }
    if( nBX0 != 1 ){
      std::cout << "Error: " << elink << ": expected pattern was not found in " << linksdata[id].size() << " words of the captured data " << std::endl;
      return false;
    }
    id++;
  }
  if ( !std::equal(positions.begin() + 1, positions.end(), positions.begin()) ){
    std::cout << "Error: " << " not all alignments patterns are in the same position " << std::endl;
    return false;
  }
  return true;
}
