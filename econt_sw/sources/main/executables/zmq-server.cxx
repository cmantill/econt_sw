#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <memory>
#include <algorithm>
#include <iomanip>

#include <signal.h>

#include <unordered_map>
#include <functional>

#include <boost/cstdint.hpp>
#include <boost/program_options.hpp>
#include <boost/timer/timer.hpp>
#include <boost/chrono.hpp>
#include <boost/thread/thread.hpp> 

#include <zmq.hpp>
#include <yaml-cpp/yaml.h>
#include <uhal/uhal.hpp>

#include "LinkAligner.h"
#include "FastControlManager.h"

namespace zmq_server{
  volatile static bool InterruptSIG = false;

  void interrupt_handler(int _ignored)
  { 
    std::cout << "\nInterrupt" << std::endl;
    InterruptSIG = true; 
  }

  enum class LinkStatusFlag{ NOT_READY, ALIGNED, READY };
};


int main(int argc,char** argv)
{
  bool m_printArgs = false;
  std::string m_input,m_connectionfile, m_devicename, m_serverport;
  int m_uhalLogLevel;
  try { 
    /** Define and parse the program options 
     */ 
    namespace po = boost::program_options; 
    po::options_description generic_options("Generic options"); 
    generic_options.add_options()
      ("help,h", "Print help messages")
      ("serverport,I", po::value<std::string>(&m_serverport)->default_value("6000"), "port of the zmq server where it listens to commands")
      ("connectionfile,f", po::value<std::string>(&m_connectionfile)->default_value("address_table/connection.xml"), "name of ipbus connection file")
      ("devicename,d", po::value<std::string>(&m_devicename)->default_value("mylittlememory"), "name of ipbus connection file")
      ("input,i", po::value<std::string>(&m_input)->default_value("/home/HGCAL_dev/src/econt_sw/econt_sw/EPORTRX_data.csv"), "input file name")
      ("uhalLogLevel,L", po::value<int>(&m_uhalLogLevel)->default_value(0), "uhal log level : 0-Disable; 1-Fatal; 2-Error; 3-Warning; 4-Notice; 5-Info; 6-Debug")
      ("printArgs", po::bool_switch(&m_printArgs)->default_value(true), "turn me on to print used arguments");
    
    po::options_description cmdline_options;
    cmdline_options.add(generic_options);

    po::variables_map vm; 
    try { 
      po::store(po::parse_command_line(argc, argv, cmdline_options),  vm); 
      if ( vm.count("help")  ) { 
	std::cout << generic_options   << std::endl; 
        return 0; 
      } 
      po::notify(vm);
    }
    catch(po::error& e) { 
      std::cerr << "ERROR: " << e.what() << std::endl << std::endl; 
      std::cerr << generic_options << std::endl; 
      return 1; 
    }

    if( m_printArgs ){ 
      if( vm.count("input") )          std::cout << "input = "          << m_input        << std::endl;
      if( vm.count("connectionfile") ) std::cout << "connectionfile = " << m_connectionfile << std::endl;
      if( vm.count("devicename") )     std::cout << "devicename = "     << m_devicename     << std::endl;
      if( vm.count("serverport") )     std::cout << "serverport = "     << m_serverport     << std::endl;
      if( vm.count("uhalLogLevel")  )  std::cout << "uhalLogLevel = "   << m_uhalLogLevel   << std::endl;
      std::cout << std::endl;
    }
  }
  catch(std::exception& e) { 
    std::cerr << "Unhandled Exception reached the top of main: " 
              << e.what() << ", application will now exit" << std::endl; 
    return 2; 
  }   

  // uHalLogLevel
  switch(m_uhalLogLevel){
  case 0:
    uhal::disableLogging();
    break;
  case 1:
    uhal::setLogLevelTo(uhal::Fatal());
    break;
  case 2:
    uhal::setLogLevelTo(uhal::Error());
    break;
  case 3:
    uhal::setLogLevelTo(uhal::Warning());
    break;
  case 4:
    uhal::setLogLevelTo(uhal::Notice());
    break;
  case 5:
    uhal::setLogLevelTo(uhal::Info());
    break;
  case 6:
    uhal::setLogLevelTo(uhal::Debug());
    break;
  }

  // set connection file
  uhal::ConnectionManager manager( "file://" + m_connectionfile );
  uhal::HwInterface m_ipbushw = manager.getDevice(m_devicename);
  uhal::HwInterface* m_ipbushwptr(&m_ipbushw);

  FastControlManager* fcptr = new FastControlManager( m_ipbushwptr );
  LinkAligner* linkaligner = new LinkAligner( m_ipbushwptr, fcptr );

  // input file
  std::ifstream infile{ m_input.c_str() };
  std::vector<std::vector<uint32_t> > dataList;
  if(infile.is_open()){
    std::string line;
    // skip the first four lines
    std::getline(infile, line);
    std::getline(infile, line);
    std::getline(infile, line);
    std::getline(infile, line);
    while (getline(infile, line)){
      if (line.empty() || line[0] == '#')
	continue;
      std::stringstream ss(line);
      std::vector<uint32_t> vec;
      uint32_t val;
      ss.ignore();
      ss.ignore();
      while(ss >> val){
	vec.push_back(val);
	if(ss.peek() == ',') ss.ignore();
	//printf("%i %x\n",val,val);
      }
      dataList.push_back(vec);
    }
  }
 

  zmq::context_t m_context(1);
  zmq::socket_t m_socket(m_context,ZMQ_REP);
  std::ostringstream os( std::ostringstream::ate );
  os.str("");
  os << "tcp://*:" << m_serverport;
  m_socket.bind(os.str().c_str()); 

  signal(SIGINT, zmq_server::interrupt_handler);

  auto reply = [&m_socket](std::string repstr){
    uint16_t size=repstr.size();
    zmq::message_t _reply(size);
    std::memcpy(_reply.data(), repstr.c_str(), size);
    m_socket.send(_reply);
  };

  auto receive = [&m_socket](bool wait=0){
    zmq::message_t message;
    if(!wait)
      m_socket.recv(&message,ZMQ_DONTWAIT);
    else
      m_socket.recv(&message);    
    std::string cmd;
    if( message.size()>0 )
      cmd = std::string(static_cast<char*>(message.data()), message.size());
    return cmd;
  };

  auto align = [&linkaligner, reply](){ 
    std::cout << " start alignment " << std::endl;
    boost::timer::cpu_timer timer;
    timer.start();
    linkaligner->align();
    timer.stop();
    std::cout << "\t\t link aligner ellapsed time = " << timer.elapsed().wall/1e9 << std::endl;
    reply("align_done");
  };


  YAML::Node m_config;
  zmq_server::LinkStatusFlag m_linkstatus = zmq_server::LinkStatusFlag::NOT_READY;
  auto configure = [&m_config, &linkaligner, &m_linkstatus, receive, reply](){
    boost::timer::cpu_timer timer;
    timer.start();
    reply("ReadyForConfig");
    auto configstr = receive(true);
    m_linkstatus = zmq_server::LinkStatusFlag::NOT_READY;
    try{
      m_config = YAML::Load(configstr)["daq"];
      std::cout << m_config << std::endl;
      auto otua = m_config["L1A_A"]["BX"].as<uint32_t>(); // just testing that the node contains something to force to try/catch something
      (void)otua;
    }
    catch( std::exception& e){
      std::cerr << "Exception : " 
      << e.what() << " yaml config file probably does not contain the expected 'daq' field" << std::endl; 
      reply("ConfigError");
      return;
    }
    //if( linkaligner->configure( m_config ) ) 
    //  reply("Configured");
    //else
   //  reply("ConfigError");
    timer.stop();
    std::cout << "\t\t configure ellapsed time = " << timer.elapsed().wall/1e9 << std::endl;
  };

  const std::unordered_map<std::string,std::function<void()> > actionMap = {
    {"align",     [&](){ align(); }},
    {"configure", [&](){ configure(); }}
  };

  while(1){
    if(zmq_server::InterruptSIG==true){
      m_socket.close();
      break;
    }
    
    std::string cmdstr = receive();
    if( cmdstr.empty()==true ){
      boost::this_thread::sleep( boost::posix_time::microseconds(100) );
    }
    else{
      std::transform(cmdstr.begin(), cmdstr.end(), cmdstr.begin(), 
		     [](const char& c){ return std::tolower(c);} );
      auto it = actionMap.find( cmdstr );
      if( it!=actionMap.end() )
	it->second();
      else{
	std::ostringstream os( std::ostringstream::ate );
	os.str(""); os << "Error " << cmdstr << " does not correspond to any entry in the action map";
	reply(os.str());
      }
    }
  }

}
