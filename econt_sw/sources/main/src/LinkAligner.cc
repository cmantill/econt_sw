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

  // input eLinks
  std::vector<std::string> eLinks;
  std::vector<std::string> outputBrams;
  auto base = std::string("link");
  for( int i=0; i<12; i++ ){
    std::string name=buildname(base,i);
    eLinks.push_back(name);
    std::string bramname=buildname(std::string("eLink_outputs_block"),i)+std::string("_bram_ctrl");
    outputBrams.push_back(bramname);
  }
  m_eLinks = eLinks;
  m_outputBrams = outputBrams;

  // output eLinks
  std::vector<std::string> eLinksOutput;
  for( int i=0; i<13; i++ ){
    std::string name=buildname(base,i);
    eLinksOutput.push_back(name);
  }
  m_eLinksOutput = eLinksOutput;

  // eLinkOutputs
  eLinkOutputsBlockHandler out( m_uhalHW,
                                std::string("eLink_outputs_ipif_stream_mux"),
				std::string("eLink_outputs_ipif_switch_mux"),
				outputBrams
                                );

  // link capture
  LinkCaptureBlockHandler lchandler( m_uhalHW,
                                     std::string("link_capture_axi"),
				     std::string("link_capture_axi_full_ipif")
				     );
  
  // IO
  IOBlockHandler fromIOhandler( m_uhalHW,
                                std::string("from_ECONT_IO_axi_to_ipif")
                                );
  IOBlockHandler toIOhandler( m_uhalHW,
                              std::string("from_ECONT_IO_axi_to_ipif")
                              );
  m_out = out;
  m_link_capture = lchandler;
  m_fromIO = fromIOhandler;
  m_toIO = toIOhandler;
}

void LinkAligner::align() {

  for(auto eLink : m_eLinks){
    // select the stream from RAM as the source 
    m_out.setSwitchRegister(eLink,"output_select",0);
    // send 255 words in the link reset pattern 
    m_out.setSwitchRegister(eLink,"n_idle_words",255);
    // send this word for almost all of the link reset pattern
    m_out.setSwitchRegister(eLink,"idle_word",ALIGN_PATTERN); 
    // send this word on BX0 during the link reset pattern
    m_out.setSwitchRegister(eLink,"idle_word_BX0",BX0_PATTERN);

    // stream one complete orbit from RAM before looping 
    m_out.setStreamRegister(eLink,"sync_mode",1); 
    // determine pattern length in orbits: 1
    m_out.setStreamRegister(eLink,"ram_range",1); 
  }

  // setting up the output RAMs
  // reading data from file
  std::string m_input = "/home/HGCAL_dev/src/econt_sw/econt_sw/EPORTRX_data.csv";
  std::ifstream infile{ m_input.c_str() };
  std::vector<std::vector<uint32_t> > dataList(12);
  if(infile.is_open()){
    std::string line;
    // skip first 4 lines
    std::getline(infile, line);
    std::getline(infile, line);
    std::getline(infile, line);
    std::getline(infile, line);
    while (getline(infile, line)){
      // skip empty lines and comments
      if (line.empty() || line[0] == '#')
        continue;
      std::stringstream ss(line);
      uint32_t val;
      ss.ignore();
      ss.ignore();
      int elink = -1;
      while(ss >> val){
	if(elink>-1) dataList.at(elink).push_back(val);
        if(ss.peek() == ',') ss.ignore();
	elink++;
      }
    }
  };


  uint32_t size_bram = 8192;
  int elink=0;
  /*
  for(auto bram : m_outputBrams){
    // special header for BX0
    dataList.at(elink).push_back(static_cast<uint32_t>(0x90000000));
    // almost all words get this header
    for(size_t i=1; i!= size_bram; ++i)
      dataList.at(elink).push_back(static_cast<uint32_t>(0xa0000000));
    std::cout << "outData " << dataList.at(elink).size() << std::endl;
    elink++;
  }
  */

  std::cout << "Input data " << dataList.at(0).size() << std::endl;
  for(unsigned int i=0; i!=dataList.at(0).size(); i++) {
    for(auto elink : dataList){
      std::cout << elink.at(i) << " ";
    }
    std::cout << std::endl;
  }

  std::cout << "Input data hex " << std::endl;
  for(unsigned int i=0; i!=dataList.at(0).size(); i++) {
    for(auto elink : dataList){
      std::cout << std::hex << std::uppercase << elink.at(i) << std::nouppercase << std::dec << " ";
    }
    std::cout << std::endl;
  }

  elink=0;
  for(auto bram : m_outputBrams){
    m_out.setData(bram, dataList.at(elink), size_bram);
    elink++;
  }

  // switching on IO
  for(auto eLink : m_eLinks){
    m_toIO.setRegister(eLink,"reg0",0b110);
    m_toIO.setRegister(eLink,"reg0",0b101);
  }
  for(auto eLink : m_eLinksOutput){
    m_fromIO.setRegister(eLink,"reg0",0b110);
    m_fromIO.setRegister(eLink,"reg0",0b101);
  }

  // sending 3 link resets to get IO delays set up properly
  //std::cout << "LinkAligner:: FC send 3 link resets, link reset counter before: " << m_fcMan->getRecvRegister("link_reset_count");
  for( int i=0; i<3; i++ ){
    m_fcMan->resetFC(); 
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
    m_fcMan->clear_link_reset();
  }
  //std::cout << " link reset counter  after " << m_fcMan->getRecvRegister("link_reset_count") << std::endl;

  // link capture
  // enable all 13 links
  m_link_capture.setRegister("global","link_enable",0x1fff);
  // reset all links
  m_link_capture.setRegister("global","explicit_resetb",0x0);
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
  m_link_capture.setRegister("global","explicit_resetb",0x1);

  for(auto eLink : m_eLinksOutput){
    // set the alignment pattern for all links
    m_link_capture.setRegister(eLink,"align_pattern",SYNC_WORD);
    // set the capture mode of all 13 links to 2 (L1A)
    m_link_capture.setRegister(eLink,"capture_mode_in",2);
    // set the BX offset of all 13 links
    uint32_t bx_offset = m_link_capture.getRegister(eLink,"L1A_offset_or_BX");
    m_link_capture.setRegister(eLink,"L1A_offset_or_BX", (bx_offset&0xffff0000)|10 );
    // set the acquire length of all 13 links
    m_link_capture.setRegister(eLink,"aquire_length", 256);
    // set the latency buffer based on the IO delays (1 or 0)
    uint32_t delay_out = m_fromIO.getRegister(eLink,"delay_out");
    m_link_capture.setRegister(eLink,"fifo_latency", 1*(delay_out<0x100));
    // tell link capture to do an acquisition
    m_link_capture.setRegister(eLink,"aquire", 1);
  }

  // sending a link reset and L1A together, to capture the reset sequence
  // set the BX on which link reset will be sent
  //std::cout << "LinkAligner:: LinkCapture, l1a counter before " << m_fcMan->getRecvRegister("l1a_count");
  m_fcMan->set_link_reset_bx(3550); // sync pattern from eLink_outputs appears in the snapshot 2 BX later? 
  m_fcMan->set_l1a_A_bx(3549); // BX on which L1A will be sent
  // send a link reset fast command and an L1A 
  m_fcMan->resetFC();
  m_fcMan->l1a_A(0x1);
  //std::cout << " l1a counter after " << m_fcMan->getRecvRegister("l1a_count") << std::endl;
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
  // clear the link reset and L1A request bits
  m_fcMan->clear_link_reset();

}

bool LinkAligner::checkLinks()
{
  // check alignment status
  for(auto elink : m_eLinksOutput){
    auto isaligned = m_link_capture.getRegister(elink,"status.link_aligned");
    if(!isaligned){
      std::cout << "Error :  " << elink << " is not aligned" << std::endl;
      return false;
    }
  }

  // check data integrity
  auto linksdata = std::vector< std::vector<uint32_t> >(m_eLinksOutput.size());
  int id=0;
  std::vector<int> positions;
  for( auto elink : m_eLinksOutput){
    uint32_t fifo_occupancy =  m_link_capture.getRegister(elink,"fifo_occupancy");
    m_link_capture.getData( elink, linksdata[id], fifo_occupancy );
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

  // another link capture
  m_link_capture.setRegister("global","explicit_resetb",0x0);
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
  m_link_capture.setRegister("global","explicit_resetb",0x1);

  for(auto eLink : m_eLinksOutput){
    // set the capture mode of all 13 links to 2 (L1A)
    m_link_capture.setRegister(eLink,"capture_mode_in",2);
    // set the acquire length of all 13 links
    m_link_capture.setRegister(eLink,"aquire_length", 256);
    // tell link capture to do an acquisition
    m_link_capture.setRegister(eLink,"aquire", 1);
  }

  // send a l1a
  m_fcMan->resetFC();
  m_fcMan->l1a_A(0x1);

  // check the captured data
  auto linksdata_new = std::vector< std::vector<uint32_t> >(m_eLinksOutput.size());
  id=0;
  for( auto elink : m_eLinksOutput){
    uint32_t fifo_occupancy =  m_link_capture.getRegister(elink,"fifo_occupancy");
    m_link_capture.getData( elink, linksdata_new[id], fifo_occupancy );
    id++;
  }

  // print captured data
  // decimal
  std::cout << "Captured data " << std::endl;
  for(unsigned int i=0; i!=linksdata_new.at(0).size(); i++) {
    std::cout << "i " << i << " ";
    for(auto elink : linksdata_new){
      std::cout << elink.at(i) << " ";
      //std::cout << std::hex << std::uppercase << elink.at(i) << std::nouppercase << std::dec << " ";                                                                                                                                                                        
    }
    std::cout << std::endl;
  }
  // hex
  std::cout << "Captured data hex size " << linksdata_new.at(0).size() << std::endl;
  for(unsigned int i=0; i!=linksdata_new.at(0).size(); i++) {
    std::cout << "i " << i << " ";
    for(auto elink : linksdata_new){
      std::cout << std::hex << std::uppercase << elink.at(i) << std::nouppercase << std::dec << " ";                                                                                                                                                                       
    }
    std::cout << std::endl;
  }

  return true;
}
