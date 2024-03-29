#ifndef LINK_ALIGNER
#define LINK_ALIGNER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>
#include <zmq.hpp>

#include <FastControlManager.h>
#include <LinkCaptureBlockHandler.h>
#include <IOBlockHandler.h>
#include <eLinkOutputsBlockHandler.h>

#define ALIGN_PATTERN 0xACCCCCCC
#define ALIGN_PATTERN_BX0 0x9CCCCCCC
#define SYNC_WORD 0b00100100010
#define BX0_WORD 0xf922f922
#define NUM_INPUTLINKS 12
#define NUM_OUTPUTLINKS 13

#define LINK_ALIGNED_COUNT_TGT 128
#define LINK_ERROR_COUNT_TGT 0

#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/vector.hpp>

class link_aligner_data{
 public:
  link_aligner_data(){;} 
  link_aligner_data( std::string link_name, int idelay, int bit_count, int error_count): m_link_name( link_name ),
    m_idelay( idelay ),
    m_bit_count( bit_count),
    m_error_count( error_count )
      {;}
  ~link_aligner_data(){;}

  std::string linkName() const { return m_link_name ; }
  int delay() const { return m_idelay ; }
  int bit_counts() const { return m_bit_count ; }
  int error_counts() const { return m_error_count ; }

 private:
  friend class boost::serialization::access;
  template<class Archive>
    void serialize(Archive & ar, const unsigned int version)
    {
      ar & m_link_name;
      ar & m_idelay;
      ar & m_bit_count;
      ar & m_error_count;
    }
  
 private:
  std::string m_link_name;
  int m_idelay;
  int m_bit_count;
  int m_error_count;
};

class LinkAligner
{
 public:
  LinkAligner(uhal::HwInterface* uhalHWInterface, FastControlManager* fc);
  ~LinkAligner(){;}

  bool configureIO(std::string, std::vector<link_description>, bool set_delay_mode=false);
  void configureData();
  bool configure(const YAML::Node& config);

  bool checkIO();
  bool checkLinkStatus(LinkCaptureBlockHandler lchandler);
  bool findBX0(LinkCaptureBlockHandler lchandler, int nwords, std::vector<int> &latencies, std::vector<int> &positions, int position_to_find);
  bool findLatency(LinkCaptureBlockHandler lchandler, std::vector<int> &positions, int nwords, int position_to_find);

  void alignIO();
  bool align();

  void testDelay(std::string elink_name, int delay);
  void delayScan();

 private:

 protected:
  uhal::HwInterface* m_uhalHW;
  FastControlManager* m_fcMan;
  int m_port;
  int m_verbose;
  int m_save_input_data;

  std::vector<link_description> m_elinksInput;
  std::vector<link_description> m_elinksOutput;

  eLinkOutputsBlockHandler m_out;
  eLinkOutputsBlockHandler m_bypass;
  IOBlockHandler m_fromIO;
  IOBlockHandler m_toIO;
  std::vector<LinkCaptureBlockHandler> m_link_capture_block_handlers;
  LinkCaptureBlockHandler m_lc_asic;
  LinkCaptureBlockHandler m_lc_emulator;
};

#endif
