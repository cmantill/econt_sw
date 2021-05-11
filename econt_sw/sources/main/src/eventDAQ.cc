#include "eventDAQ.h"

#include <sstream>
#include <fstream>

eventDAQ::eventDAQ(uhal::HwInterface* uhalHW, FastControlManager* fc)
{
  m_uhalHW = uhalHW;
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
  std::vector<std::string> eLinksOutput;
  for( int i=0; i<13; i++ ){
    std::string name=buildname(base,i);
    eLinksOutput.push_back(name);
  }
  m_eLinksOutput = eLinksOutput;

  // eLinkOutputs block (programmable data)
  eLinkOutputsBlockHandler outhandler( m_uhalHW,
				       std::string("eLink_outputs_ipif_stream_mux"),
				       std::string("eLink_outputs_ipif_switch_mux"),
				       brams
				       );

  // IO blocks 
  // toIO (input data)
  IOBlockHandler toIOhandler( m_uhalHW,
                              std::string("from_ECONT_IO_axi_to_ipif")
                              );
  // fromIO (output data)
  IOBlockHandler fromIOhandler( m_uhalHW,
                                std::string("from_ECONT_IO_axi_to_ipif")
                                );
  // link capture
  LinkCaptureBlockHandler lchandler( m_uhalHW,
                                     std::string("link_capture_axi"),
				     std::string("link_capture_axi_full_ipif"),
				     elinksInput
				     );

  m_lchandler = lchandler;
  m_out = outhandler;
  m_fromIO = fromIOhandler;
  m_toIO = toIOhandler;
}

bool eventDAQ::configure( const YAML::Node& config )
{
  // configuring programmable data
  for(auto elink : m_eLinks){
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

  // input data to ECON
  std::vector<std::vector<uint32_t> > dataList(NUM_INPUTLINKS);

  // reading data from file
  auto inputstr = config["input_file"].as< std::string >();
  std::ifstream infile{ inputstr.c_str() };
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

  // print input data
  bool printInput = true;
  if(printInput){
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
  }

  // set data to eLinkOutputs block
  int il=0; // elink iterator
  uint32_t size_bram = 8192;
  for(auto bram : m_outputBrams){
    m_out.setData(bram, dataList.at(il), size_bram);
    il++;
  }

  // switching on IO
  for(auto elink : m_eLinks){
    m_toIO.setRegister(elink,"reg0",0b110);
    m_toIO.setRegister(elink,"reg0",0b101);
  }
  for(auto elink : m_eLinksOutput){
    m_fromIO.setRegister(elink,"reg0",0b110);
    m_fromIO.setRegister(elink,"reg0",0b101);
  }

  // fc
  m_fcMan->enable_FC_stream(0x1);
  m_fcMan->enable_orbit_sync(0x1);
  m_fcMan->enable_periodic_l1a_A(0x0);
  m_fcMan->enable_periodic_l1a_B(0x0);
  m_fcMan->enable_periodic_calib_req(0x0);
  m_fcMan->enable_calib_l1a(0x0);
  m_fcMan->enable_random_l1a(0x0);

  // link capture
  for(auto elink : m_lchandler.getElinks()){
    // set the capture mode of all 13 links to 2 (L1A)
    m_lchandler.setRegister(elink,"capture_mode_in",2);
    // set the acquire length of all 13 links
    m_lchandler.setRegister(elink,"aquire_length", 256);
    // tell link capture to do an acquisition
    m_lchandler.setRegister(elink,"aquire", 1);

    uint32_t bx_offset = m_lchandler.getRegister(elink,"L1A_offset_or_BX");
    m_lchandler.setRegister(elink,"L1A_offset_or_BX", (bx_offset&0xffff0000)|10 );
  }

  return true;
}

void eventDAQ::acquire()
{
  m_fcMan->set_l1a_A_bx(3549);
  //m_fcMan->set_l1a_A_bx(0);
  std::cout << "link reset counter before: " << m_fcMan->getRecvRegister("link_reset_count") << std::endl;
  std::cout << "l1a counter before: " << m_fcMan->getRecvRegister("l1a_count") << std::endl;
  //m_fcMan->enable_periodic_l1a_A(0x1);
  m_fcMan->l1a_A(0x1);
  std::cout << " l1a counter after: " << m_fcMan->getRecvRegister("l1a_count") << std::endl;
  std::cout << "link reset counter after: " << m_fcMan->getRecvRegister("link_reset_count") << std::endl;

  m_fcMan->enable_FC_stream(0x1);
  m_fcMan->enable_orbit_sync(0x1);
  m_fcMan->link_reset(0x0);

  auto linksdata = std::vector< std::vector<uint32_t> >(m_eLinksOutput.size());
  int id=0;
  for( auto elink : m_eLinksOutput){
    uint32_t fifo_occupancy =  m_lchandler.getRegister(elink,"fifo_occupancy");
    std::cout << "fifo occ " << fifo_occupancy << std::endl;
    m_lchandler.getData( elink, linksdata[id], fifo_occupancy );
    id++;
  }
  
  bool printData = true;
  if(printData){
    std::cout << "Captured data " << std::endl;
    for(unsigned int i=0; i!=linksdata.at(0).size(); i++) {
      std::cout << "i " << i << " ";
      for(auto elink : linksdata){
	std::cout << elink.at(i) << " ";
      }
      std::cout << std::endl;
    }

    // hex
    std::cout << "Captured data hex size " << linksdata.at(0).size() << std::endl;
    for(unsigned int i=0; i!=linksdata.at(0).size(); i++) {
      std::cout << "i " << i << " ";
      for(auto elink : linksdata){
	std::cout << std::hex << std::uppercase << elink.at(i) << std::nouppercase << std::dec << " ";                                                                                                 
      }
    }
  }
}
