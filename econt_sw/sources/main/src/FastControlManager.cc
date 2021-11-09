#include <FastControlManager.h>

#include <iostream>
#include <sstream>
#include <cstring>

FastControlManager::FastControlManager(uhal::HwInterface* uhalHW,
                                       std::string fc_block_name,
                                       std::string fc_recv_block_name): m_uhalHW(uhalHW),
                                                                        m_fc_block_name(fc_block_name),
                                                                        m_fc_recv_block_name(fc_recv_block_name)
{
}

// custom
void FastControlManager::resetFC()
{
    enable_FC_stream(0x1);
    force_idles(0x0);
    enable_orbit_sync(0x1);
    prel1a_offset(0x1); // any reason for this be 0?
    enable_global_l1a(0x0);
    enable_external_l1a(0x0);
    enable_random_l1a(0x0);
    enable_block_sequencer(0x0);
    
    // set_fc_channel_A_settings(enable, bx, prescale, flavor, length, follow)
    set_fc_channel_A_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    set_fc_channel_B_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    set_fc_channel_C_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    set_fc_channel_D_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    set_fc_channel_E_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    set_fc_channel_F_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    set_fc_channel_G_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    set_fc_channel_H_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
    
}
void FastControlManager::clear_link_reset_econt()
{
    setRegister("command.enable_fast_ctrl_stream",0x1);
    setRegister("command.enable_orbit_sync",0x1);
}

// commands
void FastControlManager::enable_FC_stream(int val)
{
    setRegister("command.enable_fast_ctrl_stream",val);
}
void FastControlManager::force_idles(int val)
{
    setRegister("command.force_idles",val);
}
void FastControlManager::enable_orbit_sync(int val)
{
    setRegister("command.enable_orbit_sync",val);
}
void FastControlManager::prel1a_offset(int val)
{
    setRegister("command.prel1a_offset",val);
}
void FastControlManager::enable_global_l1a(int val)
{
    setRegister("command.global_l1a_enable",val);
}
void FastControlManager::enable_external_l1a(int val)
{
    setRegister("command.enable_external_l1as",val);
}
void FastControlManager::enable_random_l1a(int val)
{
    setRegister("command.enable_random_l1a",val);
}
void FastControlManager::enable_block_sequencer(int val)
{
    setRegister("command.enable_block_sequencer",val);
}
void FastControlManager::enable_nzs_generator(int val)
{
    setRegister("command.enable_nsz_generator",val);
}
void FastControlManager::enable_nzs_jitter(int val)
{
    setRegister("command.enable_nsz_jitter",val);
}

// requests
void FastControlManager::request_reset_nzs()
{
    setRegister("request.reset_nzs",0x1);
}
void FastControlManager::request_count_rst()
{
    setRegister("request.count_rst",0x1);
}
void FastControlManager::request_sequence()
{
    setRegister("request.sequence_req",0x1);
}
void FastControlManager::request_orbit_rst()
{
    setRegister("request.orbit_rst",0x1);
}
void FastControlManager::request_chipsynq()
{
    setRegister("request.chipsynq",0x1);
}
void FastControlManager::request_ebr()
{
    setRegister("request.ebr",0x1);
}
void FastControlManager::request_ecr()
{
    setRegister("request.ecr",0x1);
}
void FastControlManager::request_link_reset_roct()
{
    setRegister("request.link_reset_roct",0x1);
}
void FastControlManager::request_link_reset_rocd()
{
    setRegister("request.link_reset_rocd",0x1);
}
void FastControlManager::request_link_reset_econt()
{
    setRegister("request.link_reset_econt",0x1);
}
void FastControlManager::request_link_reset_econd()
{
    setRegister("request.link_reset_econd",0x1);
}

// BX for requests
void FastControlManager::bx_orbit_synq(int val)
{
    setRegister("bx_orbit_synq",val);
}
void FastControlManager::bx_chipsynq(int val)
{
    setRegister("bx_chipsynq",val);
}
void FastControlManager::bx_ebr(int val)
{
    setRegister("bx_ebr",val);
}
void FastControlManager::bx_ecr(int val)
{
    setRegister("bx_ecr",val);
}
void FastControlManager::bx_link_reset_roct(int val)
{
    setRegister("bx_link_reset_roct",val);
}
void FastControlManager::bx_link_reset_rocd(int val)
{
    setRegister("bx_link_reset_rocd",val);
}
void FastControlManager::bx_link_reset_econt(int val)
{
    setRegister("bx_link_reset_econt",val);
}
void FastControlManager::bx_link_reset_econd(int val)
{
    setRegister("bx_link_reset_econd",val);
}

// l1a settings
void FastControlManager::minimum_trigger_period(int val)
{
    setRegister("minimum_trigger_period",val);
}
void FastControlManager::random_trigger_log2_period(int val)
{
    setRegister("random_trigger_log2_period",val);
}
void FastControlManager::external_triggers_debounce(int val)
{
    setRegister("external_triggers_debounce",val);
}
void FastControlManager::external_trigger_delay(int chan, int val)
{
    char buf[200];
    sprintf(buf,"%s.%s%d",m_fc_block_name.c_str(),"external_trigger_delay.bit",chan);
    m_uhalHW->getNode(buf).write(val);
}
void FastControlManager::external_trigger_delay(int val)
{
    for(int i=0; i<4; i++)
        this->external_trigger_delay(i,val);
}

// sequencer settings
void FastControlManager::command_sequence_length(int val)
{
    setRegister("command_sequence.length",val);
}
void FastControlManager::command_sequence_bx(int val)
{
    setRegister("command_sequence.bx",val);
}
void FastControlManager::command_sequence_orbit_prescale(int val)
{
    setRegister("command_sequence.orbit_prescale",val);
}
void FastControlManager::command_sequence_page(int val)
{
    setRegister("command_sequence.page",val);
}
void FastControlManager::command_sequence_contents(const std::vector<uint32_t>& vec)
{
    char buf[200];
    sprintf(buf,"%s.%s",m_fc_block_name.c_str(),"command_sequence.contents");
    m_uhalHW->getNode(buf).writeBlock(vec);
}

// periodic generator settings
void FastControlManager::set_fc_periodic_settings(int periodic_chan, int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow)
{
    char enablebuf[200], flavorbuf[200], enablefollowbuf[200], followwhichbuf[200], bxbuf[200], prescalebuf[200], lengthbuf[200];
    sprintf(enablebuf      ,"%s.%s%d%s",m_fc_block_name.c_str(),"periodic",periodic_chan,".enable");
    sprintf(flavorbuf      ,"%s.%s%d%s",m_fc_block_name.c_str(),"periodic",periodic_chan,".flavor");
    sprintf(enablefollowbuf,"%s.%s%d%s",m_fc_block_name.c_str(),"periodic",periodic_chan,".enable_follow");
    sprintf(followwhichbuf ,"%s.%s%d%s",m_fc_block_name.c_str(),"periodic",periodic_chan,".follow_which");
    sprintf(bxbuf          ,"%s.%s%d%s",m_fc_block_name.c_str(),"periodic",periodic_chan,".bx");
    sprintf(prescalebuf    ,"%s.%s%d%s",m_fc_block_name.c_str(),"periodic",periodic_chan,".orbit_prescale");
    sprintf(lengthbuf      ,"%s.%s%d%s",m_fc_block_name.c_str(),"periodic",periodic_chan,".burst_length");
    
    switch(flavor){
    case FC_channel_flavor::L1A       : m_uhalHW->getNode(flavorbuf).write(0x0); break;
    case FC_channel_flavor::L1A_NZS   : m_uhalHW->getNode(flavorbuf).write(0x1); break;
    case FC_channel_flavor::CALPULINT : m_uhalHW->getNode(flavorbuf).write(0x2); break;
    case FC_channel_flavor::CALPULEXT : m_uhalHW->getNode(flavorbuf).write(0x3); break;
    case FC_channel_flavor::EXTPULSE0 : m_uhalHW->getNode(flavorbuf).write(0x4); break;
    case FC_channel_flavor::EXTPULSE1 : m_uhalHW->getNode(flavorbuf).write(0x5); break;
    }
    switch(follow){
    case FC_channel_follow::DISABLE  : m_uhalHW->getNode(enablefollowbuf).write(0x0); break;
    case FC_channel_follow::A:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x0); break;
    case FC_channel_follow::B:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x1); break;
    case FC_channel_follow::C:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x2); break;
    case FC_channel_follow::D:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x3); break;
    case FC_channel_follow::E:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x4); break;
    case FC_channel_follow::F:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x5); break;
    case FC_channel_follow::G:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x6); break;
    case FC_channel_follow::H:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x7); break;
    }
    m_uhalHW->getNode(enablebuf).write(enable);
    m_uhalHW->getNode(bxbuf).write(bx);
    m_uhalHW->getNode(prescalebuf).write(prescale);
    m_uhalHW->getNode(lengthbuf).write(length);
}

void FastControlManager::set_fc_channel_A_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow)
{
    this->set_fc_periodic_settings(0, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_B_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
    this->set_fc_periodic_settings(1, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_C_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
    this->set_fc_periodic_settings(2, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_D_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
    this->set_fc_periodic_settings(3, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_E_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
    this->set_fc_periodic_settings(4, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_F_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
    this->set_fc_periodic_settings(5, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_G_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
    this->set_fc_periodic_settings(6, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_H_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow)
{
    this->set_fc_periodic_settings(7, enable, bx, prescale, flavor, length, follow);
} 

void FastControlManager::setRegister( std::string reg, int val )
{
    char buf[200];
    sprintf(buf,"%s.%s",m_fc_block_name.c_str(),reg.c_str());
    m_uhalHW->getNode(buf).write(val);
}

void FastControlManager::setRecvRegister( std::string reg, int val )
{
    char buf[200];
    sprintf(buf,"%s.%s",m_fc_recv_block_name.c_str(),reg.c_str());
    m_uhalHW->getNode(buf).write(val);
}

const uint32_t FastControlManager::getRegister( std::string reg )
{
    char buf[200];
    sprintf(buf,"%s.%s",m_fc_block_name.c_str(),reg.c_str());
    uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
    m_uhalHW->dispatch();
    return (uint32_t)val;
}

const uint32_t FastControlManager::getRecvRegister( std::string reg )
{
    char buf[200];
    sprintf(buf,"%s.%s",m_fc_recv_block_name.c_str(),reg.c_str());
    uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
    m_uhalHW->dispatch();
    return (uint32_t)val;
}
