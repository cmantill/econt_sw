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

#include "spdlog/spdlog.h"
//#include "spdlog/cfg/env.h"

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
    
    // eLinksOutput
    std::vector<std::string> brams;
    for( int i=0; i<NUM_INPUTLINKS; i++ ){
        std::stringstream ss; ss << std::setfill('0') << std::setw(2) << i;
        std::string bramname=std::string("test-vectors-to-ASIC-and-emulator-test-vectors-out-block")+ss.str()+std::string("-bram-ctrl");
        brams.push_back(bramname);
    }
    eLinkOutputsBlockHandler outhandler( m_uhalHW,
                                         std::string("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux"),
                                         std::string("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux"),
                                         brams,
                                         m_elinksInput
        );
    m_out = outhandler;
    //spdlog::cfg::load_env_levels();
    //spdlog::info("LinkAligner: initialized");
}

bool LinkAligner::configure_data()
{
    // configure eLinkOutputs
    for(auto elink : m_out.getElinks()){
        // select the stream from RAM as the source 
        m_out.setSwitchRegister(elink.name(),"output_select",0);
        // send 255 words in the link reset pattern 
        m_out.setSwitchRegister(elink.name(),"n_idle_words",255);
        // send this word for almost all of the link reset pattern
        m_out.setSwitchRegister(elink.name(),"idle_word",ALIGN_PATTERN); 
        // send this word on BX0 during the link reset pattern
        m_out.setSwitchRegister(elink.name(),"idle_word_BX0",ALIGN_PATTERN_BX0);
        // stream one complete orbit from RAM before looping 
        m_out.setStreamRegister(elink.name(),"sync_mode",1); 
        // determine pattern length in orbits: 1
        m_out.setStreamRegister(elink.name(),"ram_range",1); 
    }
    
    // zero data with headers in output RAMs
    int il=0;
    uint32_t size_bram = 8192;
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
    return true;
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
        if(set_delay_mode){
            // set delay mode to automatic delay setting
            IOhandler.setRegister(elink.name(),"reg0.reset_link",0);
            IOhandler.setRegister(elink.name(),"reg0.reset_counters",1);
            IOhandler.setRegister(elink.name(),"reg0.delay_mode",1);
        }
    }

    // global reset
    IOhandler.setGlobalRegister("global_rstb_links",1);
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
        m_link_capture_block_handlers.push_back(lchandler_asic);
        

        LinkCaptureBlockHandler lchandler_emulator( m_uhalHW,
                                                    std::string("capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0"),
                                                    std::string("capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0"),
                                                    m_elinksOutput );
        //m_link_capture_block_handlers.push_back(lchandler_emulator)
;
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
    // for ASIC (from tester)
    for(auto elink : m_out.getElinks()){
        // select PRBS mode
        m_out.setSwitchRegister(elink.name(),"output_select",1);
    }
    
    // check fromIO
    for(auto elink : m_fromIO.getElinks()){
        std::cout << "LinkAligner: delay mode fromIO " << m_fromIO.getRegister(elink.name(),"reg0.delay_mode") <<std::endl;
        std::cout << "LinkAligner: waiting for transitions fromIO " << m_fromIO.getRegister(elink.name(),"reg3.waiting_for_transitions") <<std::endl;
        int delay_ready = m_fromIO.getRegister(elink.name(),"reg3.delay_ready");
        if(delay_ready!=1){
            std::cout << "LinkAligner Warning: fromIO delay-ready " << delay_ready << std::endl;
        }
    }
}

void LinkAligner::align() {  
    
    // align IO blocks
    align_IO();  
    
    // configure data
    bool isdata = configure_data();
    
    // reset FC
    m_fcMan->resetFC();
    
    // reset counters (not working)
    m_fcMan->setRecvRegister("command.reset_counters_io",0);
    m_fcMan->setRecvRegister("command.reset_counters_io",1);
    
    /**
     * 32 bit word alignment
     *
     * Need to issue Link-Reset-ROC-T:
     * - will cause ROC (or in this case eLinkOutputsBlock) to send training pattern:
     *   - ALIGN_PATTERN: 0xaccccccc
     *   - ALIGN_PATTERN_BX0: 0x9ccccccc
     * - sync pattern from eLink_outputs appears in the snapshot 2 BX later 
     * - ECON-T will take a 6 BX snapshot
     *   - the snapshot delay is programmable via i2c
     *   - and will align its inputs (find the 32bit word boundaries and determine skew between each eRx)
     *
     **/
    if(m_verbose>0){
        int roct_counters = m_fcMan->getRecvRegister("counters.link_reset_roct");
        std::cout << "LinkAligner: # Link-Reset-ROC-T FC: " << roct_counters << std::endl;
    }
    m_fcMan->request_link_reset_roct();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    if(m_verbose>0){
        int roct_counters =m_fcMan->getRecvRegister("counters.link_reset_roct");
        std::cout << "LinkAligner: # Link-Reset-ROC-T FC + 1: " << roct_counters << std::endl;
    } 
    
    /** 
     * Aligning link capture:
     *
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
    
    // reset and configure all links in link capture
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
            // set the capture mode of all 13 links to manual
            lchandler.setRegister(elink.name(),"capture_mode_in",1); // 2 (L1A), 1 (manual)
            // set the BX offset of all 13 links
            lchandler.setRegister(elink.name(),"L1A_offset_or_BX",3554);
            // set the acquire length of all 13 links
            lchandler.setRegister(elink.name(),"aquire_length",0x1000); // 4096 max memory of link capture
            // set the latency buffer based on the IO delays (1 or 0)
            // fifo_latency: delays some links relative to one another before they go into the memory
            uint32_t delay_out = m_fromIO.getRegister(elink.name(),"reg3.delay_out");
            lchandler.setRegister(elink.name(),"fifo_latency", 1*(delay_out<0x100));
            // tell link capture to do an acquisition
            //lchandler.setRegister(elink.name(),"aquire", 1);
        }
        
        if(m_verbose){
            int econt_counters =m_fcMan->getRecvRegister("counters.link_reset_econt");
            std::cout << "LinkAligner: # Link-Reset-ECON-T FC: " << econt_counters << std::endl;   
        }
        
        // set bx on which link reset econt will be sent
        m_fcMan->bx_link_reset_econt(3555);
        
        // send an aquire and link reset as close as possible
        char buf[200];
        sprintf(buf,"%s.global.aquire",lchandler.name().c_str());
        m_uhalHW->getNode(buf).write(0x0);
        m_uhalHW->getNode(buf).write(0x1);

        /*
        for(auto elink : lchandler.getElinks()){
            //lchandler.setRegister(elink.name(),"aquire", 1);
            char buf[200];
            sprintf(buf,"%s.%s.aquire",lchandler.name().c_str(),elink.name().c_str());
            m_uhalHW->getNode(buf).write(0x1);
        }
        */
        sprintf(buf,"%s.request.link_reset_econt",m_fcMan->name().c_str());
        m_uhalHW->getNode(buf).write(0x1);
        m_uhalHW->dispatch();

        sprintf(buf,"%s.global.aquire",lchandler.name().c_str());
        m_uhalHW->getNode(buf).write(0x0);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
        m_uhalHW->dispatch();
        
        //m_fcMan->request_link_reset_econt();
        
        if(m_verbose){
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
            int econt_counters =m_fcMan->getRecvRegister("counters.link_reset_econt");
            std::cout << "LinkAligner: # Link-Reset-ECON-T FC: " << econt_counters << std::endl;
        }
        
        // check link capture counters
        for(auto elink : lchandler.getElinks()){
            auto aligned = lchandler.getRegister(elink.name(),"link_aligned_count");  
            auto errors  = lchandler.getRegister(elink.name(),"link_error_count");
            if(m_verbose){
                std::cout << "LinkAligner: LC counters for " << elink.name().c_str()  << std::endl;
                if( aligned==LINK_ALIGNED_COUNT_TGT && errors==LINK_ERROR_COUNT_TGT ){
                    std::cout << "LinkAligner: Correct counters for link alignment: aligned " << aligned << " errors " << errors << std::endl;
                }
                else{
                    std::cout << "LinkAligner: Warning! Incorrect counters for link alignemnt: aligned " << aligned << " errors " << errors << std::endl;
                }
            }
        }
    } // end link capture handlers loop
}

bool LinkAligner::checkLinks()
{
  for(auto lchandler : m_link_capture_block_handlers){
    // check alignment status
    for( auto elink : lchandler.getElinks() ){
      auto isaligned = lchandler.getRegister(elink.name(),"status.link_aligned");
      if(!isaligned){
	std::cout << "LinkAligner: Error :  " << elink.name().c_str() << " is not aligned" << std::endl;
	//return false;
      }
      lchandler.setRegister(elink.name(),"aquire", 1);
    }
    
    // check data integrity
    auto linksdata = std::vector< std::vector<uint32_t> >(NUM_OUTPUTLINKS);
    int id=0;
    std::vector<int> positions;
    for( auto elink : lchandler.getElinks() ){
      uint32_t fifo_occupancy =  lchandler.getRegister(elink.name(),"fifo_occupancy");
      lchandler.getData( elink.name(), linksdata[id], fifo_occupancy );
      
      // check where BX0 pattern is found
      int nBX0 = (int)std::count( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
      auto posit = std::find( linksdata[id].begin(), linksdata[id].end(), BX0_WORD );
      if (posit !=  linksdata[id].end()){
	positions.push_back(posit - linksdata[id].begin());
	std::cout << "LinkAligner: found for " << elink.name() << " in " << posit - linksdata[id].begin() << std::endl;
      }
      if( nBX0 != 1 ){
	std::cout << "LinkAligner Error: " << elink.name() << ": expected pattern was not found in " << linksdata[id].size() << " words of the captured data " << std::endl;
	//return false;
      }
      id++;
      lchandler.setRegister(elink.name(),"explicit_rstb_acquire", 0);
      lchandler.setRegister(elink.name(),"explicit_rstb_acquire", 1);
      lchandler.setGlobalRegister("interrupt_enable", 0x0);
    }
    //if ( !std::equal(positions.begin() + 1, positions.end(), positions.begin()) ){
    //  std::cout << "LinkAligner: Error: " << " not all alignments patterns are in the same position " << std::endl;
    //return false;
    //}
    
    // print captured data
    bool printData = true;
    if(printData){
      std::cout << "LinkAligner: Captured data hex size " << linksdata.at(0).size() << std::endl;
      for(unsigned int i=0; i!=linksdata.at(0).size(); i++) {
	std::cout << "i " << i << " ";
	for(auto link_data : linksdata){
	  std::cout << boost::format("0x%08x") % link_data.at(i) << " ";
	}
	std::cout << std::endl;
      }
    }
  
    std::cout << "LinkAligner: Links Aligned " << std::endl;
  }
  return true;
}

void LinkAligner::testPRBS(){
  std::cout << "LinkAligner: starting PRBS28" << std::endl;
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
