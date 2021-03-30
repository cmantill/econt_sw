#ifndef LINKCAPTUREBLOCKHANDLER
#define LINKCAPTUREBLOCKHANDLER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>

class LinkCaptureBlockHandler
{
 public:
  LinkCaptureBlockHandler(){;}
  LinkCaptureBlockHandler(uhal::HwInterface* uhalHW,
			  std::string link_capture_block_name);
  ~LinkCaptureBlockHandler(){;}

  const std::string name() const { return m_link_capture_block_name; }

  void setRegister(std::string elink, std::string regName, uint32_t value);
  void setGlobalRegister(std::string regName, uint32_t value);
  const uint32_t getRegister(std::string elink,std::string regName);
  const uint32_t getGlobalRegister(std::string regName);

 private:
  uhal::HwInterface* m_uhalHW;
  std::string m_link_capture_block_name; //same names as in the address_table/fw_block_addresses.xml file 
};

#endif
