#ifndef LINKCAPTUREBLOCKHANDLER
#define LINKCAPTUREBLOCKHANDLER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>

class link_description{
 public:
  link_description(){;}
  link_description(std::string name, int polarity, int code ) :
    _name(name),
    _polarity(polarity),
    _code(code)
    { ; }
  std::string name() const { return _name; }
  int polarity() const { return _polarity; }
  int code()     const { return _code; }

  friend struct YAML::convert<link_description>;

 private:
  std::string _name;
  int _polarity;
  int _code;
};

namespace YAML {
  template<>
    struct convert<link_description> {
    static Node encode(const link_description& rhs) {
      Node node;
      node["name"]     = rhs._name;
      node["polarity"] = rhs._polarity;
      node["code"]     = rhs._code;
      return node;
    }

    static bool decode(const Node& node, link_description& rhs) {
      if(!node.IsMap() || node.size() != 3) {
        return false;
      }
      auto amap = node.as< std::map<std::string,std::string> >();
      rhs._name     = amap["name"];
      rhs._polarity = atoi( amap["polarity"].c_str() );
      rhs._code     = atoi( amap["idcode"].c_str() );
      return true;
    }
  };
}

class LinkCaptureBlockHandler
{
 public:
  LinkCaptureBlockHandler(){;}
  LinkCaptureBlockHandler(uhal::HwInterface* uhalHW,
			  std::string link_capture_block_name,
			  std::string bram_name,
			  std::vector< link_description > & elinks
			  );
  ~LinkCaptureBlockHandler(){;}

  const std::string name() const { return m_link_capture_block_name; }
  const std::string bramName() const { return m_bram_name; }
  const std::vector< link_description > & getElinks() const {return m_elinks; }

  void setRegister(std::string elink, std::string regName, uint32_t value);
  void setRegister(std::string regName, uint32_t value); // if elink not specified, it will on all member of m_elinks and set the register to the same value
  void setGlobalRegister(std::string regName, uint32_t value);
  const uint32_t getRegister(std::string elink,std::string regName);
  const uint32_t getGlobalRegister(std::string regName);
  void getData(std::string elink, std::vector<uint32_t> &data, uint32_t size);

 private:
  uhal::HwInterface* m_uhalHW;
  std::string m_link_capture_block_name; //same names as in the address_table/fw_block_addresses.xml file 
  std::string m_bram_name;
  std::vector< link_description > m_elinks;
};

#endif
