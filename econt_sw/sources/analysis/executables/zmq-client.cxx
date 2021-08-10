#include <iostream>
#include <fstream>
#include <sstream>
#include <signal.h>
#include <unordered_map>

#include <boost/cstdint.hpp>
#include <boost/program_options.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/thread/thread.hpp>

#include <zmq.hpp>
#include <yaml-cpp/yaml.h>

#include "pullerFSM.h"
#include "datawriter.h"

namespace zmq_client{
  volatile static bool InterruptSIG = false;

  void interrupt_handler(int _ignored)
  { 
    std::cout << "\nInterrupt" << std::endl;
    InterruptSIG = true; 
  }
};

enum class DataType{ DELAY_SCAN };

int main(int argc,char** argv)
{
  std::string m_masterPort;
  bool m_printArgs = false;
  try {
    namespace po = boost::program_options; 
    po::options_description generic_options("Generic options"); 
    generic_options.add_options()
      ("help,h", "Print help messages")
      ("masterPort,P",   po::value<std::string>(&m_masterPort)->default_value("6001"), "port used to communicate with the master scripts (will be used as a REQ/REQ socket)")
      ("printArgs",      po::bool_switch(&m_printArgs)->default_value(false), "turn me on to print used arguments");
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
      std::cout << "masterPort = " << m_masterPort << std::endl;
      std::cout << std::endl;
    }
  }
  catch(std::exception& e) { 
    std::cerr << "Unhandled Exception reached the top of main: " 
              << e.what() << ", application will now exit" << std::endl; 
    return 2; 
  }   
  

  // declare sockets
  zmq::context_t m_context(1);
  zmq::socket_t m_socket(m_context,ZMQ_REP );
  zmq::socket_t m_puller(m_context,ZMQ_PULL);
  std::ostringstream os( std::ostringstream::ate );
  os.str("");
  os << "tcp://*:" << m_masterPort;
  m_socket.bind(os.str().c_str()); 

  signal(SIGINT, zmq_client::interrupt_handler);

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

  
  YAML::Node m_config;
  pullerFSM fsm;
  auto configure = [&m_config, receive, reply, &fsm](){
    reply("ReadyForConfig");
    auto configstr = receive(true);
    try{
      m_config = YAML::Load(configstr)["global"];
      std::cout << m_config << std::endl;
      auto otua = m_config["serverIP"].as<std::string>(); // just testing that the node contains something to force to try/catch something
      (void)otua;
    }
    catch( std::exception& e){
      std::cerr << "Exception : " 
      << e.what() << " yaml config file probably does not contain the expected 'global' field" << std::endl; 
      reply("ConfigError");
      return;
    }
    if( fsm.reset() ) {} // fsm state : initialised
    reply("Configured");
  };

  auto readdata = [&m_puller, &m_config, &fsm](){
    std::ostringstream os(std::ostringstream::ate);
    os.str();
    os << "tcp://" << m_config["serverIP"].as<std::string>() << ":" << m_config["data_push_port"].as<std::string>();
    std::cout << "Looking at data in " << os.str().c_str() << std::endl;
    m_puller.connect(os.str());

    if( !fsm.start() ) {// fsm state : running
      return; //this would be a code implementation issue
    } 

    int fileID=0;
    DataType dtype;
    while( fsm.status()!="Destroyed" ){
      zmq::message_t messageStart;
      m_puller.recv(&messageStart,ZMQ_DONTWAIT);
      if( messageStart.size()==0 && fsm.status()=="Stopped" ){
	if( !fsm.destroy() ) {// fsm state : destroyed
	  return; //this would be a code implementation issue
	} 
	continue;
      }
      else if( messageStart.size()==0 ){
	boost::this_thread::sleep( boost::posix_time::milliseconds(100) );
	continue;
      }
      else{
	std::string start_str( static_cast<char*>(messageStart.data()), messageStart.size() );
        if( start_str.compare("START_DELAY_SCAN")==0 )
	  dtype = DataType::DELAY_SCAN;
	else{
	  std::cout << "There is a major issue in reading data: we received '" << start_str << "' instead of expected START run strings -> (wait 10 seconds)" << std::endl;
	  boost::this_thread::sleep( boost::posix_time::seconds(10) );
	  continue;
	}
	DataWriterFactory fac;
	std::unique_ptr<Writer> writer;
	os.str("");
	os << m_config["output_directory"].as<std::string>() << fileID;
	std::cout << "DataType = " << int(dtype) << std::endl;
	switch( dtype ){
	case DataType::DELAY_SCAN:
	  os << ".csv";
	  writer = fac.Create("delayscan",os.str());
	  std::cout << start_str << "\t save delay scan data in : " << os.str() << std::endl;
	  break;
	}
	
	link_aligner_data lad;
	while( fsm.status()!="Destroyed" ){
	  zmq::message_t message;
	  m_puller.recv(&message);
	  std::string dataStr( static_cast<char*>(message.data()), message.size() );
	  if( dataStr.compare("END_OF_RUN")==0 ){
	    std::cout << dataStr << std::endl;
	    break;
	  }
    
	  std::istringstream iss(dataStr);
	  boost::archive::binary_iarchive ia{iss};
	  while(1){
	    try{
	      switch( dtype ){
	      case DataType::DELAY_SCAN:
		ia >> lad;
		std::cout << " filling " << std::endl;
		writer->fill(lad);
		break;
	      }
	    }
	    catch( std::exception& e ){
	      break;
	    }
	  }
	}
	writer->save();
	fileID++;
      }
    }
    try{
      char ep[1024];
      size_t s = sizeof(ep);
      m_puller.getsockopt( ZMQ_LAST_ENDPOINT,&ep,&s );
      m_puller.disconnect( ep );
    }
    catch(...)
      {}
  }; // end readdata
  
  
  boost::thread readdatathread;
  auto start = [&readdatathread,readdata,reply](){ 
    readdatathread = boost::thread( readdata );
    reply("Data puller running");
  };

  auto stop = [&readdatathread,&fsm,reply](bool fromCMD=true){
    if( fromCMD==true ){
      if( fsm.stop() ) { }// fsm state : stopped
    }
    else{
      if( fsm.destroy() ) { }// fsm state : destroyed
    }
    readdatathread.join();
    if(fromCMD==true) //don't send a reply if stop comes from ctrl-c 
      reply("Data puller stopped");
  };

  const std::unordered_map<std::string,std::function<void()> > actionMap = {
    {"configure", [&](){ configure(); }},
    {"start",     [&](){ start();     }},
    {"stop",      [&](){ stop();      }}
  };

  while(1){
    if(zmq_client::InterruptSIG==true){
      stop(false);
      boost::this_thread::sleep( boost::posix_time::milliseconds(100) );
      break;
    }
    
    std::string cmdstr = receive();
    if( cmdstr.empty()==true ){
      boost::this_thread::sleep( boost::posix_time::milliseconds(100) );
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

  return 0;
}
