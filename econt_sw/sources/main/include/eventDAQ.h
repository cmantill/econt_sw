#ifndef EVENTDAQ_H_
#define EVENTDAQ_H_

#include <uhal/uhal.hpp>
#include <zmq.hpp>
#include <yaml-cpp/yaml.h>

#include "LinkCaptureBlockHandler.h"
#include "FastControlManager.h"
#include "IOBlockHandler.h"
#include "eLinkOutputsBlockHandler.h"

#define NUM_INPUTLINKS 12
#define NUM_OUTPUTLINKS 13
#define ALIGN_PATTERN 0xACCCCCCC
#define BX0_PATTERN 0x9CCCCCCC
#define SYNC_WORD 0b00100100010
#define BX0_WORD 0xf922f922

class eventDAQ
{
 public:
  eventDAQ(uhal::HwInterface* uhalHW, FastControlManager* fc);
  ~eventDAQ();

  bool configure( const YAML::Node& config );

  void run();
  void configurelinks();
  void acquire();

 private:
  uhal::HwInterface* m_uhalHW;
  FastControlManager* m_fcMan;

  eLinkOutputsBlockHandler m_out;
  LinkCaptureBlockHandler m_lchandler;

};

#endif
