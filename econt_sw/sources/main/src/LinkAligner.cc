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
  
  m_elinksInput.clear();
  m_elinksOutput.clear();
  
  // input elinks
  for( int i=0; i<NUM_INPUTLINKS; i++ ){
    std::string name=buildname(base,i);
    link_description desc(name, 1, i); //setting elink idcode to i 
    m_elinksInput.push_back(desc);
  }
  
  // output links
  for( int i=0; i<NUM_OUTPUTLINKS; i++ ){
    std::string name=buildname(base,i);
    link_description desc(name, 1, i); //setting elink idcode to i
    m_elinksOutput.push_back(desc);
  }
  
  // test-vectors and bypass
  std::vector<std::string> brams,brams_bypass;
  for( int i=0; i<NUM_INPUTLINKS; i++ ){
    std::stringstream ss; ss << std::setfill('0') << std::setw(2) << i;
    brams.push_back(std::string("test-vectors-to-ASIC-and-emulator-test-vectors-out-block")+ss.str()+std::string("-bram-ctrl"));
    brams_bypass.push_back(std::string("econt-emulator-bypass-option-expected-outputs-RAM-out-block")+ss.str()+std::string("-bram-ctrl"));
  }
  eLinkOutputsBlockHandler outhandler( m_uhalHW,
				       std::string("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux"),
				       std::string("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux"),
				       brams,
				       m_elinksInput
				       );

  eLinkOutputsBlockHandler bypasshandler( m_uhalHW,
					  std::string("econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux"),
					  std::string("econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux"),
					  brams_bypass,
					  m_elinksInput
					  );
  
  m_out = outhandler;
  m_bypass = bypasshandler;
}

bool LinkAligner::configure_IO(std::string IO_block_name, std::vector<link_description> elinks, bool set_delay_mode)
{
  IOBlockHandler IOhandler( m_uhalHW,
			    IO_block_name,
			    elinks
			    );
  
  for(auto elink : IOhandler.getElinks()){
    // setting to 1 will disable the output
    IOhandler.setRegister(elink.name(),"reg0.tristate_IOBUF",0);
    IOhandler.setRegister(elink.name(),"reg0.bypass_IOBUF",0);

    // do not invert the output
    IOhandler.setRegister(elink.name(),"reg0.invert",0);
    IOhandler.setRegister(elink.name(),"reg0.reset_link",0);
    IOhandler.setRegister(elink.name(),"reg0.reset_counters",1);
    if(set_delay_mode){
      // set delay mode to automatic setting
      IOhandler.setRegister(elink.name(),"reg0.delay_mode",1);
    }
    else{
      IOhandler.setRegister(elink.name(),"reg0.delay_mode",0);
    }
  }
  // global reset
  IOhandler.setGlobalRegister("global_rstb_links",1);
  IOhandler.setGlobalRegister("global_reset_counters",1);
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
  IOhandler.setGlobalRegister("global_latch_counters",1);

  return true;
}

bool LinkAligner::configure_data()
{
  // setup normal output in test-vectors
  for(auto elink : m_out.getElinks()){
    // select the stream from RAM as the source 
    m_out.setSwitchRegister(elink.name(),"output_select",0);
    // send 256 words in the link reset pattern 
    m_out.setSwitchRegister(elink.name(),"n_idle_words",256);
    // send this word for almost all BXs of the link reset pattern
    m_out.setSwitchRegister(elink.name(),"idle_word",ALIGN_PATTERN); 
    // send this word on BX0 during the link reset pattern
    m_out.setSwitchRegister(elink.name(),"idle_word_BX0",ALIGN_PATTERN_BX0);
    // headers
    m_out.setSwitchRegister(elink.name(),"header_mask",0xf0000000);
    m_out.setSwitchRegister(elink.name(),"header",0xa0000000);
    m_out.setSwitchRegister(elink.name(),"header_BX0",0x90000000);
    // stream one complete orbit from RAM before looping 
    m_out.setStreamRegister(elink.name(),"sync_mode",1); 
    // determine pattern length in orbits: 1
    m_out.setStreamRegister(elink.name(),"ram_range",1);
    m_out.setStreamRegister(elink.name(),"force_sync",0);
  }
  
  // set zero data with headers 
  int il=0;
  uint32_t size_bram = 4096; // bram size (not the one on uHal)
  std::vector<std::vector<uint32_t> > dataList;
  for(auto bram : m_out.getBrams()){
    std::vector<uint32_t> outData;
    outData.push_back(static_cast<uint32_t>(0x90000000)); 
    for(size_t i=1; i!= size_bram; ++i) 
      outData.push_back(static_cast<uint32_t>(0xa0000000));
    dataList.push_back(outData);
    m_out.setData(bram, outData, size_bram);
    //spdlog::debug("LinkAligner: out bram {}.{0:d} size {0:d}",bram,il,outData.size())
    il++;
  }
  
  /*
  //spdlog::debug("LinkAligner: Input data {0:d}",dataList.at(0).size());
  for(unsigned int i=0; i<dataList.at(0).size(); ++i) {
  for(auto elink : dataList) {
  //spdlog::debug("LinkAligner: Link{0:d}, {0:08x}",elink.at(i));
  
  }
  }
  */

  // configure bypass
  for(auto elink : m_out.getElinks()){
    // select data from the emulator as the source
    m_bypass.setSwitchRegister(elink.name(),"output_select",1);
  }
  
  return true;
}

bool LinkAligner::configure(const YAML::Node& config)
{
  try{
    auto outelinks = config["elinks_out"].as< std::vector<link_description> >();
    m_port = config["delay_scan_port"].as<int>();
    m_verbose = config["verbose"].as<int>();
    m_save_input_data = config["save_input_data"].as<int>();
    
    m_link_capture_block_handlers.clear();
    m_elinksOutput = outelinks;
    
    LinkCaptureBlockHandler lchandler_asic( m_uhalHW,
					    std::string("capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0"),
					    std::string("capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0_FIFO"),
					    m_elinksOutput );
    m_link_capture_block_handlers.push_back(lchandler_asic); // first lc is ASIC
    m_lc_asic = lchandler_asic;
    
    LinkCaptureBlockHandler lchandler_emulator( m_uhalHW,
						std::string("capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0"),
						std::string("capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0"),
						m_elinksOutput );
    m_link_capture_block_handlers.push_back(lchandler_emulator); // second lc is emulator
    m_lc_emulator = lchandler_emulator;
    
    if( configure_IO(std::string("ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0"), m_elinksInput) &&
	configure_IO(std::string("ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"), m_elinksOutput, true)
	){
      IOBlockHandler toIOhandler( m_uhalHW,
				  std::string("ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0"),
				  m_elinksInput );
      m_toIO = toIOhandler;
      IOBlockHandler fromIOhandler( m_uhalHW,
				    std::string("ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"),
				    m_elinksOutput );
      m_fromIO = fromIOhandler;
      std::cout << "configure IO " << std::endl;
      return true;
    }
    else 
      return false;
  }
  catch( std::exception& e){
    std::cerr << "Exception : "
	      << e.what() << " yaml config file probably does not contain the expected 'delay_scan_port' entries" << std::endl;
    return false;
  }
}

void LinkAligner::align_IO() {
  // generate bit transitions 
  for(auto elink : m_out.getElinks()){
    // select PRBS mode
    m_out.setSwitchRegister(elink.name(),"output_select",1);
  }
  
  // wait for user input after sending PRBS
  std::cout << "IO blocks configured. Sending PRBS. Press key to continue... " << std::endl;
  std::cin.get();
  
  // check that from-IO is aligned
  for(auto elink : m_fromIO.getElinks()){
    std::cout << "LinkAligner: delay mode fromIO " << m_fromIO.getRegister(elink.name(),"reg0.delay_mode") <<std::endl;
    std::cout << "LinkAligner: waiting for transitions fromIO " << m_fromIO.getRegister(elink.name(),"reg3.waiting_for_transitions") <<std::endl;
    int delay_ready = m_fromIO.getRegister(elink.name(),"reg3.delay_ready");
    if(delay_ready!=1){
      std::cout << "LinkAligner Warning: fromIO delay-ready " << delay_ready << std::endl;
    }
  }
}

bool LinkAligner::checkLinkStatus(LinkCaptureBlockHandler lchandler)
{
  // check alignment status
  for( auto elink : lchandler.getElinks() ){
    auto aligned = lchandler.getRegister(elink.name(),"link_aligned_count");
    auto errors  = lchandler.getRegister(elink.name(),"link_error_count");
    auto isaligned = lchandler.getRegister(elink.name(),"status.link_aligned");
    if( aligned==LINK_ALIGNED_COUNT_TGT && errors==LINK_ERROR_COUNT_TGT && isaligned){
      std::cout << "LinkAligner: Link aligned: " << elink.name().c_str() << " correct counters: aligned " << aligned << " errors " << errors << std::endl;
    }
    if(!isaligned){
      std::cout << "LinkAligner: Error :  " << elink.name().c_str() << " is not aligned" << std::endl;
      if(m_verbose){
        std::cout << "LinkAligner: Warning! Incorrect counters for link alignemnt: aligned " << aligned << " errors " << errors << std::endl;
      }
      return false;
    }
  }
  return true;
}
bool LinkAligner::checkLinkFIFO(LinkCaptureBlockHandler lchandler,std::vector<int> positions,,std::vector<int> positions_found)
{
  // check that fifos have the same occupancy
  while(1){
      std::vector<int> fifo_occupancies;
      for( auto elink : lchandler.getElinks() ){
          uint32_t fifo_occupancy =  lchandler.getRegister(elink.name(),"fifo_occupancy");
          fifo_occupancies.push_back( (int)fifo_occupancy);
      }
      if ( std::adjacent_find( fifo_occupancies.begin(), fifo_occupancies.end(), std::not_equal_to<>() ) == fifo_occupancies.end() )
      {
          std::cout << "All fifo occupancies are the same " << std::endl;
          break;
      }
  }

  // check data integrity
  auto linksdata = std::vector< std::vector<uint32_t> >(NUM_OUTPUTLINKS);
  int id=0;
  positions.clear();
  for( auto elink : lchandler.getElinks() ){
    uint32_t fifo_occupancy =  lchandler.getRegister(elink.name(),"fifo_occupancy");
    lchandler.getData( elink.name(), linksdata[id], fifo_occupancy );

    // check where BX0 pattern is found
    if(fifo_occupancy>0){
        int nBX0 = (int)std::count( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
        auto posit = std::find( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
        if (posit !=  linksdata[id].end()){
            positions.push_back(posit - linksdata[id].begin());
            std::cout << "LinkAligner: found for " << elink.name() << " in " << posit - linksdata[id].begin() << std::endl;
        }
        if( nBX0 == 0 ){
            std::cout << "LinkAligner Error: " << elink.name() << ": expected pattern was not found in " << linksdata[id].size() << " words of the captured data " << std::endl;
        }
      return false;
    }
    id++;
  }
  if(positions.size()>0){
    if ( !std::equal(positions.begin() + 1, positions.end(), positions.begin()) ){
      std::cout << "LinkAligner: Error: " << " not all alignments patterns are in the same position " << std::endl;
      return false;
    }
    return true;
  }
  else{
    return false;
  }
}
bool LinkAligner::findLatency(std::vector<int> latencies,LinkCaptureBlockHandler lchandler,std::vector<int> found_positions)
{
  // set latency
  for(auto elink : lchandler.getElinks()){
      lchandler.setRegister(elink.name(),"fifo_latency",latencies.at();
  }

  // global acquire
  lchandler.setRegister("global","aquire",0);
  lchandler.setRegister("global","aquire",1);

  // send link reset ECONT
  m_fcMan->bx_link_reset_econt(3550);
  m_fcMan->request_link_reset_econt();

  // reset global acquire
  lchandler.setRegister("global","aquire",0);

  // find BX0 word on link capture for ASIC
  if(
  if( checkLinks( m_lc_asic ) && checkLinks( m_lc_emulator )){
    return true;
  }
  else
    return false;
}

/**
 * Phase alignment: performed by IO-blocks/eLinkOutputs
 *
 * 32 bit word alignment for ECON-T:
 * Need to issue Link-Reset-ROC-T and see status 0x3 in i2c registers:
 * - will cause ROC (or in this case eLinkOutputsBlock) to send training pattern:
 *   - ALIGN_PATTERN: 0xaccccccc
 *   - ALIGN_PATTERN_BX0: 0x9ccccccc
 * - sync pattern from eLink_outputs appears in the snapshot 2 BX later
 * - ECON-T will take a 6 BX snapshot
 *   - the snapshot delay is programmable via i2c
 *   - and will align its inputs (find the 32bit word boundaries and determine skew between each eRx)
 *
 * Aligning link capture:
 * Need to issue Link-Reset-ECON-T and capture data:
 * - need to set the BX on which Link-Reset will be sent
 * - will cause ECON-T to produce its training pattern for 256BX:
 *   - 5 bits of the BX counter (which counts 0 -- 15 and then repeats, except for BX0 where it is 31 instead)
 *   - 11 bit TxSyncWord set via i2c, (as default set to 0x122)
 *   e.g.
 *     - 0xf922f922 for BX0
 *     - 0x01220122 for BX16 (when counter rolls back into 0)
 *     - 0x09220922 for BX1
 *     - 0x11221222 for BX2
 *     - 0x59225922 for BX11 etc
 * - link capture will look for this pattern and align its inputs
 *   - we can send a L1A (FC ROCv2) or set a BX on which to capture
 **/

bool LinkAligner::align() {  
  
  // align IO blocks
  align_IO();  
  
  // configure data
  bool isdata = configure_data();
  
  // reset FC
  m_fcMan->resetFC();
  
  // reset FC counters (not working)
  m_fcMan->setRecvRegister("command.reset_counters_io",0);
  m_fcMan->setRecvRegister("command.reset_counters_io",1);
  
  // set bx at which link resets will be sent
  m_fcMan->bx_link_reset_roct(3500);
  m_fcMan->bx_link_reset_rocd(3501);
  m_fcMan->bx_link_reset_econt(3502);
  m_fcMan->bx_link_reset_econd(3503);
  
  if(m_verbose>0){
    std::cout << "LinkAligner: # Link-Reset-ROC-T FC: " << m_fcMan->getRecvRegister("counters.link_reset_roct") << std::endl;
  }
  
  // send link reset roc-t
  m_fcMan->request_link_reset_roct();
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
  
  if(m_verbose>0){
    int roct_counters =m_fcMan->getRecvRegister("counters.link_reset_roct");
    std::cout << "LinkAligner: # Link-Reset-ROC-T FC + 1: " << roct_counters << std::endl;
  }
  
  // wait for user input
  std::cout << "Sent link reset ROCT. Press key to continue..." << std::endl;
  std::cin.get();
  
  // configure link captures for alignment
  for(auto lchandler : m_link_capture_block_handlers){
    // enable all 13 links
    lchandler.setRegister("global","link_enable",0x1fff);
    // reset all links
    lchandler.setRegister("global","explicit_resetb",0x0);
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
    lchandler.setRegister("global","explicit_resetb",0x1);
    for(auto elink : lchandler.getElinks()){
      // set the alignment pattern for all links (by default 0x122)
      lchandler.setRegister(elink.name(),"align_pattern",SYNC_WORD);
      // set the BX offset of all 13 links
      lchandler.setRegister(elink.name(),"L1A_offset_or_BX",0);
      
      // set the capture mode of a link-reset-econt
      lchandler.setRegister(elink.name(),"capture_mode_in",2); // 2 (Link-reset), 1 (manual)
      lchandler.setRegister(elink.name(),"capture_linkreset_ECONt",1);
      lchandler.setRegister(elink.name(),"capture_L1A",0);
      lchandler.setRegister(elink.name(),"capture_linkreset_ROCd",0);
      lchandler.setRegister(elink.name(),"capture_linkreset_ROCt",0);
      lchandler.setRegister(elink.name(),"capture_linkreset_ECONd",0);
      
      // set the acquire length of all 13 links
      lchandler.setRegister(elink.name(),"aquire_length",0x1000); // 4096 max memory of link capture
    }
  }

  // send link reset econt
  if(m_verbose>0){
     std::cout << "LinkAligner: # Link-Reset-ECON-T FC: " << m_fcMan->getRecvRegister("counters.link_reset_econt") << std::endl;
  }
  m_fcMan->request_link_reset_econt();
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
  if(m_verbose>0){
      std::cout << "LinkAligner: # Link-Reset-ECON-T FC: " << m_fcMan->getRecvRegister("counters.link_reset_econt") << std::endl;
  }

  // check link alignment
  if(checkLinkStatus(m_lc_asic)){

      for( int i=0; i<511; i++ ){
          if(alignRelative(i)){
              std::cout << "LinkAligner: found emulator latency " << i << std::endl;
              break;
          }
      }
  }
  else{
      std::cout << "LinkAligner: ASIC link capture links are not aligned after link-reset-econt" << std::endl;
      return false;
  }
  return true;
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
