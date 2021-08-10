#include "eventDAQ.h"

#include <sstream>
#include <fstream>
#include <chrono>
#include <thread>
#include <boost/format.hpp>

eventDAQ::eventDAQ(uhal::HwInterface* uhalHW, FastControlManager* fc)
{
  m_uhalHW = uhalHW;
  m_fcMan = fc;

  auto buildname = [](std::string base, int val)->std::string{ return base+std::to_string(val); };
  auto base = std::string("link");

  std::vector<link_description> elinksInput;
  std::vector<link_description> elinksOutput;

  // input links
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

  // eLinkOutputs block (programmable data)
  eLinkOutputsBlockHandler outhandler( m_uhalHW,
				       std::string("eLink_outputs_ipif_stream_mux"),
				       std::string("eLink_outputs_ipif_switch_mux"),
				       brams,
				       elinksInput
				       );

  // link capture
  LinkCaptureBlockHandler lchandler( m_uhalHW,
                                     std::string("link_capture_axi"),
				     std::string("link_capture_axi_full_ipif"),
				     elinksOutput
				     );

  m_lchandler = lchandler;
  m_out = outhandler;
}

bool eventDAQ::configure( const YAML::Node& config )
{
  // input file string
  inputstr = config["input_file"].as< std::string >();

  // fast commands
  m_fcMan->enable_FC_stream(0x1);
  m_fcMan->enable_orbit_sync(0x1);

  return true;
}

bool eventDAQ::read()
{

  // input data to ECON
  std::vector<std::vector<uint32_t> > dataList(NUM_INPUTLINKS);

  // reading data from file
  std::ifstream infile{ inputstr.c_str() };
  if(infile.is_open()){
    int id=0;
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
        if(elink>-1) {
	  if((val&0xF0000000)!=0) std::cout << "header not zero " << std::endl;
	  // add headers
	  if(id==0){
	    val |= 0x90000000;
	  }
	  else{
	    val |= 0xa0000000;
	  }
	  dataList.at(elink).push_back(static_cast<uint32_t>(val));
	}
        if(ss.peek() == ',') ss.ignore();
	elink++;
      }
      if(elink>-1) id++;
    }
  }
  else{
    return false;
  }

  // print input data
  bool printInput = true;
  if(printInput){
    std::cout << "Input data " << dataList.at(0).size() << std::endl;
    for(unsigned int i=0; i<dataList.at(0).size(); ++i) {
      for(auto elink : dataList) {
	//std::cout << elink.at(i) << " ";
	std::cout << boost::format("0x%08x") % elink.at(i) << " ";
        //std::cout << std::hex << elink.at(i) << std::dec << " ";
      }
      std::cout << std::endl;
    }
  }

  // set data to eLinkOutputs block
  int il=0; // elink iterator
  uint32_t size_bram = 8192;
  for(auto bram : m_out.getBrams()){
    std::vector<uint32_t> outData;
    //outData.push_back(static_cast<uint32_t>(0x90000000)); 
    for(size_t i=0; i<dataList.at(0).size(); i++) { 
	outData.push_back(dataList.at(il).at(i));
    }
    for(size_t i=dataList.at(0).size(); i< size_bram; ++i) {
      outData.push_back(static_cast<uint32_t>(0xa0000000));
    }
    m_out.setData(bram, outData, size_bram);
    il++;
  }

  return true;
}

void eventDAQ::configurelinks()
{
  // link capture
  m_lchandler.setGlobalRegister("aquire",0x1);

  for(auto elink : m_lchandler.getElinks()){
    m_lchandler.setRegister(elink.name(),"explicit_rstb_acquire", 0x0);
    m_lchandler.setRegister(elink.name(),"explicit_rstb_acquire", 0x1);
    // set the capture mode of all 13 links to 2 (L1A)
    m_lchandler.setRegister(elink.name(),"capture_mode_in",2);
    // set the acquire length of all 13 links
    //m_lchandler.setRegister(elink.name(),"aquire_length", 4096);
    m_lchandler.setRegister(elink.name(),"aquire_length", 256);
    // tell link capture to do an acquisition
    m_lchandler.setRegister(elink.name(),"aquire", 1);
  }
}

void eventDAQ::acquire()
{
  configurelinks();

  //m_fcMan->set_l1a_A_bx(3549);
  m_fcMan->set_l1a_A_bx(0);
  m_fcMan->l1a_A(0x1);
  std::this_thread::sleep_for(std::chrono::milliseconds(1));

  m_fcMan->enable_FC_stream(0x1);
  m_fcMan->enable_orbit_sync(0x1);

  auto linksdata = std::vector< std::vector<uint32_t> >(NUM_OUTPUTLINKS);
  int id=0;
  for( auto elink : m_lchandler.getElinks()){
    uint32_t fifo_occupancy =  m_lchandler.getRegister(elink.name(),"fifo_occupancy");
    m_lchandler.getData( elink.name(), linksdata[id], fifo_occupancy );
    id++;
  }
  
  bool printData = true;
  if(printData){
    std::cout << "Captured data hex size " << linksdata.at(0).size() << std::endl;
    for(unsigned int i=0; i!=linksdata.at(0).size(); i++) {
      std::cout << "i " << i << " ";
      for(auto elink : linksdata){
	std::cout << boost::format("0x%08x") % elink.at(i) << " ";
	//std::cout << std::hex << elink.at(i) << std::dec << " ";
      }
      std::cout << std::endl;
    }

  }
}
