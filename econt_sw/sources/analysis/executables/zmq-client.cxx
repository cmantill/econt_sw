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

namespace zmq_client{
  volatile static bool InterruptSIG = false;

  void interrupt_handler(int _ignored)
  { 
    std::cout << "\nInterrupt" << std::endl;
    InterruptSIG = true; 
  }
};

int main(int argc,char** argv)
{
  std::string m_masterIP, m_masterPort;
  bool m_printArgs = false;
  try { 
    namespace po = boost::program_options; 
    po::options_description generic_options("Generic options"); 
    generic_options.add_options()
      ("help,h", "Print help messages")
      ("masterIP,I",     po::value<std::string>(&m_masterIP)->default_value("localhost"), "ip address (or alias) of the master zmq server (which is sending config)")
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
      std::cout << "masterIP = "   << m_masterIP   << std::endl;
      std::cout << "masterPort = " << m_masterPort << std::endl;
      std::cout << std::endl;
    }
  }
  catch(std::exception& e) { 
    std::cerr << "Unhandled Exception reached the top of main: " 
              << e.what() << ", application will now exit" << std::endl; 
    return 2; 
  }  

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

}
