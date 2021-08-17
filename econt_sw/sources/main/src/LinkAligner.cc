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

  std::vector<link_description> elinksInput;
  std::vector<link_description> elinksOutput;

  // input elinks
  std::vector<std::string> brams;
  for( int i=0; i<NUM_INPUTLINKS; i++ ){
    std::string name=buildname(base,i);
    link_description desc(name, 1, i); //setting idcode to i (can add that later)
    elinksInput.push_back(desc);
    std::string bramname=buildname(std::string("eLink_outputs_block"),i)+std::string("_bram_ctrl");
    brams.push_back(bramname);
  }

  // output links                                                                                                                                                            
  for( int i=0; i<NUM_OUTPUTLINKS; i++ ){
    std::string name=buildname(base,i);
    link_description desc(name, 1, i); //setting idcode to i                                                                                                                                                                                                               
    elinksOutput.push_back(desc);
  }

  // link capture
  LinkCaptureBlockHandler lchandler( m_uhalHW,
                                     std::string("link_capture_axi"),
				     std::string("link_capture_axi_full_ipif"),
				     elinksOutput
				     );
  // toIO (input data)
  IOBlockHandler toIOhandler( m_uhalHW,
                              std::string("to_ECONT_IO_axi_to_ipif"),
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

bool LinkAligner::configure(const YAML::Node& config) 
{

  try{
    auto outelinks = config["elinks_out"].as< std::vector<link_description> >();
    LinkCaptureBlockHandler lchandler( m_uhalHW,
				       std::string("link_capture_axi"),
				       std::string("link_capture_axi_full_ipif"),
				       outelinks);
    m_lchandler = lchandler;
    m_port = config["delay_scan_port"].as<int>();
  }
  catch( std::exception& e){
    std::cerr << "Exception : "
              << e.what() << " yaml config file probably does not contain the expected 'delay_scan_port' entries" << std::endl;
    return false;
  }

  // configuring programmable data in elinkOutputs block
  for(auto elink : m_out.getElinks()){
    // select the stream from RAM as the source 
    m_out.setSwitchRegister(elink.name(),"output_select",0);
    // send 255 words in the link reset pattern 
    m_out.setSwitchRegister(elink.name(),"n_idle_words",255);
    // send this word for almost all of the link reset pattern
    m_out.setSwitchRegister(elink.name(),"idle_word",ALIGN_PATTERN); 
    // send this word on BX0 during the link reset pattern
    m_out.setSwitchRegister(elink.name(),"idle_word_BX0",BX0_PATTERN);

    // stream one complete orbit from RAM before looping 
    m_out.setStreamRegister(elink.name(),"sync_mode",1); 
    // determine pattern length in orbits: 1
    m_out.setStreamRegister(elink.name(),"ram_range",1); 
  }

  // Setting up the output RAMs
  int il=0;
  uint32_t size_bram = 8192;
  std::vector<std::vector<uint32_t> > dataList;
  for(auto bram : m_out.getBrams()){
    std::cout << "bram " << bram << " il " << il << std::endl;
    std::vector<uint32_t> outData;
    outData.push_back(static_cast<uint32_t>(0x90000000)); 
    for(size_t i=1; i!= size_bram; ++i) 
      outData.push_back(static_cast<uint32_t>(0xa0000000));
    dataList.push_back(outData);
    m_out.setData(bram, outData, size_bram);
    std::cout << " size " << outData.size() << std::endl;
    il++;
  }
  
  /*
  std::cout << "Input data " << dataList.at(0).size() << std::endl;
  for(unsigned int i=0; i<dataList.at(0).size(); ++i) {
    for(auto elink : dataList) {
      //std::cout << elink.at(i) << " ";
      std::cout << boost::format("0x%08x") % elink.at(i) << " ";
      //std::cout << std::hex << elink.at(i) << std::dec << " ";
    }
    std::cout << std::endl;
  }
  */

  return true;
}

void LinkAligner::align() {  
  // switching on IO
  for(auto elink : m_toIO.getElinks()){
    // active-low reset
    m_toIO.setRegister(elink.name(),"reg0.reset_link",0);
    // reset counters (active-high reset)
    m_toIO.setRegister(elink.name(),"reg0.reset_counters",1);
    // delay mode to automatic delay setting
    m_toIO.setRegister(elink.name(),"reg0.delay_mode",1);
    // run normally
    m_toIO.setRegister(elink.name(),"reg0.reset_counters",0);
    m_toIO.setRegister(elink.name(),"reg0.reset_link",1);
  }

  for(auto elink : m_fromIO.getElinks()){
    m_fromIO.setRegister(elink.name(),"reg0.reset_link",0);
    m_fromIO.setRegister(elink.name(),"reg0.reset_counters",1);
    m_fromIO.setRegister(elink.name(),"reg0.delay_mode",1);
    m_fromIO.setRegister(elink.name(),"reg0.reset_counters",0);
    m_fromIO.setRegister(elink.name(),"reg0.reset_link",1);
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
    m_lchandler.setRegister(elink.name(),"align_pattern",SYNC_WORD);
    // set the capture mode of all 13 links to 2 (L1A)
    m_lchandler.setRegister(elink.name(),"capture_mode_in",2);
    // set the BX offset of all 13 links
    uint32_t bx_offset = m_lchandler.getRegister(elink.name(),"L1A_offset_or_BX");
    m_lchandler.setRegister(elink.name(),"L1A_offset_or_BX", (bx_offset&0xffff0000)|10 );
    // set the acquire length of all 13 links
    m_lchandler.setRegister(elink.name(),"aquire_length", 256);
    // set the latency buffer based on the IO delays (1 or 0)
    uint32_t delay_out = m_fromIO.getRegister(elink.name(),"reg3.delay_out");
    m_lchandler.setRegister(elink.name(),"fifo_latency", 1*(delay_out<0x100));
    // tell link capture to do an acquisition
    m_lchandler.setRegister(elink.name(),"aquire", 1);
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

  std::cout << "l1a counter after: " << m_fcMan->getRecvRegister("l1a_count") << std::endl;
  std::cout << "link reset counter after: " << m_fcMan->getRecvRegister("link_reset_count") << std::endl;

  for(auto elink : m_lchandler.getElinks()){
    auto aligned = m_lchandler.getRegister(elink.name(),"link_aligned_count");  
    auto errors  = m_lchandler.getRegister(elink.name(),"link_error_count");
    if( aligned==LINK_ALIGNED_COUNT_TGT && errors==LINK_ERROR_COUNT_TGT ){
      std::cout << "Correct counters for link alignment " << std::endl;
    }
    else{
      std::cout << "aligned " << aligned << " errors " << errors << " for " << elink.name().c_str() << std::endl;;
    }
  }
  
}

bool LinkAligner::checkLinks()
{
  // check alignment status
  for( auto elink : m_lchandler.getElinks() ){
    auto isaligned = m_lchandler.getRegister(elink.name(),"status.link_aligned");
    if(!isaligned){
      std::cout << "Error :  " << elink.name().c_str() << " is not aligned" << std::endl;
      //return false;
    }
    m_lchandler.setRegister(elink.name(),"aquire", 1);
  }

  // check data integrity
  auto linksdata = std::vector< std::vector<uint32_t> >(NUM_OUTPUTLINKS);
  int id=0;
  std::vector<int> positions;
  for( auto elink : m_lchandler.getElinks() ){
    uint32_t fifo_occupancy =  m_lchandler.getRegister(elink.name(),"fifo_occupancy");
    m_lchandler.getData( elink.name(), linksdata[id], fifo_occupancy );
    
    // check where BX0 pattern is found
    int nBX0 = (int)std::count( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
    auto posit = std::find( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
    if (posit !=  linksdata[id].end()){
      positions.push_back(posit - linksdata[id].begin());
    }
    if( nBX0 != 1 ){
      std::cout << "Error: " << elink.name() << ": expected pattern was not found in " << linksdata[id].size() << " words of the captured data " << std::endl;
      //return false;
    }
    id++;
    m_lchandler.setRegister(elink.name(),"explicit_rstb_acquire", 0);
    m_lchandler.setRegister(elink.name(),"explicit_rstb_acquire", 1);
    m_lchandler.setGlobalRegister("interrupt_enable", 0x0);
  }
  if ( !std::equal(positions.begin() + 1, positions.end(), positions.begin()) ){
    std::cout << "Error: " << " not all alignments patterns are in the same position " << std::endl;
    //return false;
  }

  // print captured data
  bool printData = false;
  if(printData){
    std::cout << "Captured data hex size " << linksdata.at(0).size() << std::endl;
    for(unsigned int i=0; i!=linksdata.at(0).size(); i++) {
      std::cout << "i " << i << " ";
      for(auto link_data : linksdata){
	std::cout << boost::format("0x%08x") % link_data.at(i) << " ";
      }
      std::cout << std::endl;
    }
  }
  
  //return false;
  std::cout << "Links Aligned " << std::endl;
  return true;
}

void LinkAligner::testPRBS(){
  std::cout << " starting PRBS28" << std::endl;
  for(auto elink : m_out.getElinks()){
    m_out.setSwitchRegister(elink.name(),"header_mask",0xf0000000);
    m_out.setSwitchRegister(elink.name(),"header",0xa0000000);
    m_out.setSwitchRegister(elink.name(),"header_BX0",0x90000000);
  }

}

void LinkAligner::testDelay(std::string elink_name, int delay) {
  // bound delays (9 bits: 2^9=511)
  delay = delay>=0 ? delay : 0;
  delay = delay<=503 ? delay : 503; // 503+8=511

  m_fromIO.setRegister(elink_name,"reg0.reset_counters",1);
  m_fromIO.setRegister(elink_name,"reg0.delay_mode",0); // delay mode to manual delay setting
  m_fromIO.setRegister(elink_name,"reg0.delay_in",delay);
  m_fromIO.setRegister(elink_name,"reg0.delay_offset",8); 

  m_fromIO.setRegister(elink_name,"reg0.delay_set",1); // this sets the delays

  m_fromIO.setRegister(elink_name,"reg0.reset_counters",0);

  while(1){
    auto delayready = m_fromIO.getRegister(elink_name,"reg3.delay_ready");
    auto delayout = m_fromIO.getRegister(elink_name,"reg3.delay_out");
    if((int)delayout==delay && delayready==1){
      break;
    }
    else{
      sleep(0.1);
    }
  }
}

void LinkAligner::delayScan() {
  std::ostringstream os( std::ostringstream::ate );

  auto context = std::unique_ptr<zmq::context_t>( new zmq::context_t(1) );
  auto pusher = std::unique_ptr<zmq::socket_t>( new zmq::socket_t(*context,ZMQ_PUSH) );
  if( m_port>-1 ){
    os.str("");
    os << "tcp://*:" << m_port;
    pusher->bind(os.str().c_str()); 
    std::string _str("START_DELAY_SCAN");
    zmq::message_t message0(_str.size());
    memcpy(message0.data(), _str.c_str(), _str.size());
    pusher->send(message0);
  }

  std::ostringstream zos( std::ios::binary );
  boost::archive::binary_oarchive oas{zos};

  // loop over delay taps
  for( int idelay=0; idelay<504; idelay=idelay+8 ){
    
    // set delays and wait until delay_ready
    for(auto elink : m_fromIO.getElinks()){
      testDelay( elink.name(), idelay);
    }

    // reset the counters (no longer necessary to write clear the reset by writing 0, the reset will clear itself)
    m_fromIO.setGlobalRegister("global_reset_counters", 1);

    // wait for some amount of time
    sleep(0.1);
    
    //  latch the counters (saves counter values for all links) 
    m_fromIO.setGlobalRegister("global_latch_counters", 1);

    for(auto elink : m_fromIO.getElinks()){
      // read bit_counter (counts the number of bytes) and error_counter (counts the number of bytes that had at least one bit error - didn't match between P and N side)
      auto bit_counts = m_fromIO.getRegister(elink.name(),"bit_counter");
      auto error_counts  = m_fromIO.getRegister(elink.name(),"error_counter");

      // get elink name and save lad
      os.str("");
      os <<  m_fromIO.name() << "." << elink.name();
      std::string link_name = os.str();
      link_aligner_data lad( link_name, idelay, bit_counts, error_counts);
      oas << lad;
    }
  }
  
  if( m_port>-1 ){
    zmq::message_t message(zos.str().size());
    memcpy(message.data(), zos.str().c_str(), zos.str().size());
    pusher->send(message);
  }

  // send: end of run
  if( m_port>-1 ){
    std::string _str("END_OF_RUN");
    zmq::message_t message2(_str.size());
    memcpy(message2.data(), _str.c_str(), _str.size());
    pusher->send(message2);
  } 


  try{
    char ep[1024];
    size_t s = sizeof(ep);
    pusher->getsockopt( ZMQ_LAST_ENDPOINT,&ep,&s );
    pusher->unbind( ep );
  }
  catch(...)//this should only happen if the pusher was not yet bounded to anything
    {}
}
