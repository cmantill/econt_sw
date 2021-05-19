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
#include <boost/format.hpp>

LinkAligner::LinkAligner(uhal::HwInterface* uhalHWInterface, 
			 FastControlManager* fc)
{
  m_uhalHW = uhalHWInterface;
  m_fcMan = fc;

  auto buildname = [](std::string base, int val)->std::string{ return base+std::to_string(val); };
  auto base = std::string("link");

  // input links
  std::vector<std::string> elinksInput;
  std::vector<std::string> brams;
  for( int i=0; i<NUM_INPUTLINKS; i++ ){
    std::string name=buildname(base,i);
    elinksInput.push_back(name);
    std::string bramname=buildname(std::string("eLink_outputs_block"),i)+std::string("_bram_ctrl");
    brams.push_back(bramname);
  }

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
  // toIO (input data)
  IOBlockHandler toIOhandler( m_uhalHW,
                              std::string("from_ECONT_IO_axi_to_ipif"),
			      elinksInput
                              );
  // fromIO (output data)
  IOBlockHandler fromIOhandler( m_uhalHW,
                                std::string("from_ECONT_IO_axi_to_ipif"),
				elinksOutput
                                );

  // eLinkOutputs block (programmable data)
  eLinkOutputsBlockHandler outhandler( m_uhalHW,
				       std::string("eLink_outputs_ipif_stream_mux"),
				       std::string("eLink_outputs_ipif_switch_mux"),
				       brams,
				       elinksInput
				       );
  m_lchandler = lchandler;
  m_fromIO = fromIOhandler;
  m_toIO = toIOhandler;
  m_out = outhandler;

}

bool LinkAligner::configure() 
{
  // configuring programmable data
  for(auto elink : m_out.getElinks()){
    // select the stream from RAM as the source 
    m_out.setSwitchRegister(elink,"output_select",0);
    // send 255 words in the link reset pattern 
    m_out.setSwitchRegister(elink,"n_idle_words",255);
    // send this word for almost all of the link reset pattern
    m_out.setSwitchRegister(elink,"idle_word",ALIGN_PATTERN); 
    // send this word on BX0 during the link reset pattern
    m_out.setSwitchRegister(elink,"idle_word_BX0",BX0_PATTERN);

    // stream one complete orbit from RAM before looping 
    m_out.setStreamRegister(elink,"sync_mode",1); 
    // determine pattern length in orbits: 1
    m_out.setStreamRegister(elink,"ram_range",1); 
  }

  // Setting up the output RAMs
  int il=0; // elink iterator
  uint32_t size_bram = 8192;
  for(auto bram : m_out.getBrams()){
    std::vector<uint32_t> outData;
    outData.push_back(static_cast<uint32_t>(0x90000000)); 
    for(size_t i=1; i!= size_bram; ++i) 
      outData.push_back(static_cast<uint32_t>(0xa0000000));
    m_out.setData(bram, outData, size_bram);
    il++;
  }

  return true;
}

void LinkAligner::align() {  
  // switching on IO
  for(auto elink : m_toIO.getElinks()){
    // active-low reset
    m_toIO.setRegister(elink,"reg0.reset_link",0);
    // reset counters (active-high reset)
    m_toIO.setRegister(elink,"reg0.reset_counters",1);
    // delay mode to automatic delay setting
    m_toIO.setRegister(elink,"reg0.delay_mode",1);
    // run normally
    m_toIO.setRegister(elink,"reg0.reset_counters",0);
    m_toIO.setRegister(elink,"reg0.reset_link",1);
  }
  for(auto elink : m_fromIO.getElinks()){
    m_fromIO.setRegister(elink,"reg0.reset_link",0);
    m_fromIO.setRegister(elink,"reg0.reset_counters",1);
    m_fromIO.setRegister(elink,"reg0.delay_mode",1);
    m_fromIO.setRegister(elink,"reg0.reset_counters",0);
    m_fromIO.setRegister(elink,"reg0.reset_link",1);
  }

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
    m_lchandler.setRegister(elink,"aquire", 1);
  }

  // check data integrity
  auto linksdata = std::vector< std::vector<uint32_t> >(NUM_OUTPUTLINKS);
  int id=0;
  std::vector<int> positions;
  for( auto elink : m_lchandler.getElinks() ){
    uint32_t fifo_occupancy =  m_lchandler.getRegister(elink,"fifo_occupancy");
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
    m_lchandler.setRegister(elink,"explicit_rstb_acquire", 0);
    m_lchandler.setRegister(elink,"explicit_rstb_acquire", 1);
    m_lchandler.setGlobalRegister("interrupt_enable", 0x0);
  }
  if ( !std::equal(positions.begin() + 1, positions.end(), positions.begin()) ){
    std::cout << "Error: " << " not all alignments patterns are in the same position " << std::endl;
    return false;
  }

  bool printData = true;
  if(printData){
    std::cout << "Captured data hex size " << linksdata.at(0).size() << std::endl;
    for(unsigned int i=0; i!=linksdata.at(0).size(); i++) {
      std::cout << "i " << i << " ";
      for(auto elink : linksdata){
	std::cout << boost::format("0x%08x") % elink.at(i) << " ";
      }
      std::cout << std::endl;
    }

  }

  std::cout << "Links Aligned " << std::endl;
  return true;
}
