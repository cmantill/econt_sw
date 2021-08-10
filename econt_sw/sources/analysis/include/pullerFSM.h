#ifndef PULLER_FSM
#define PULLER_FSM 1

#include <boost/msm/back/state_machine.hpp>
#include <boost/msm/front/state_machine_def.hpp>

#include <boost/thread/thread.hpp>

namespace msm = boost::msm;
namespace mpl = boost::mpl;

namespace pullerfsm{

  struct start   {};
  struct stop    {};
  struct destroy {};
  struct reset   {};

  // front-end: define the FSM structure 
  struct puller_fsm : public msm::front::state_machine_def<puller_fsm>
  {

    // The list of FSM states
    struct Initialised : public msm::front::state<> {};

    struct Running : public msm::front::state<> {};

    struct Stopped : public msm::front::state<> {};

    struct Destroyed : public msm::front::state<> {};

    // the initial state of the player SM. Must be defined
    typedef Initialised initial_state;

    // transition actions
    void Start(start const&)        { }
    void Stop(stop const&)          { }
    void Reset(reset const&)        { }
    void Destroy(destroy const&)    { }

    // Transition table for puller_fsm
    struct transition_table : mpl::vector<
      //    Start     Event         Next      Action Guard
      //  +---------+-------------+---------+---------------------+----------------------+
      a_row < Initialised,  start,      Running,     &puller_fsm::Start>,
      a_row < Running,      stop,       Stopped,     &puller_fsm::Stop>,
      a_row < Stopped,      destroy,    Destroyed,   &puller_fsm::Destroy>,
      a_row < Running,      destroy,    Destroyed,   &puller_fsm::Destroy>,
      a_row < Initialised,  destroy,    Destroyed,   &puller_fsm::Destroy>,
      a_row < Running,      destroy,    Destroyed,   &puller_fsm::Destroy>,
      a_row < Destroyed,    destroy,    Destroyed,   &puller_fsm::Destroy>,
      a_row < Destroyed,    reset,      Initialised, &puller_fsm::Reset>,
      a_row < Initialised,  reset,      Initialised, &puller_fsm::Reset>
      //  +---------+-------------+---------+---------------------+----------------------+
      > {};
    // Replaces the default no-transition response.
    template <class FSM,class Event>
      void no_transition(Event const& e, FSM&,int state)
    {
      return;
    }
  };
  typedef msm::back::state_machine<puller_fsm> FSM;
  static char const* const state_names[] = { "Initialised", "Running", "Stopped", "Destroyed" };
}
 
class pullerFSM{
 public:
  pullerFSM()
    { 
      m_mutex.lock();
      m_fsm.start(); 
      m_mutex.unlock();
    }
  ~pullerFSM()
    { 
      m_mutex.lock();
      m_fsm.stop(); 
      m_mutex.unlock();
    }

  std::string status() const { return pullerfsm::state_names[ m_fsm.current_state()[0] ]; }
  
  bool start()
  {
    m_mutex.lock();
    if( m_fsm.process_event(pullerfsm::start())!=boost::msm::back::HANDLED_TRUE ){
      std::cout << "impossible to process start when state is " << status() << std::endl;
      m_mutex.unlock();
      return false;
    }
    m_mutex.unlock();
    return true;
  }

  bool stop()
  {
    m_mutex.lock();
    if( m_fsm.process_event(pullerfsm::stop())!=boost::msm::back::HANDLED_TRUE ){
      std::cout << "impossible to process stop when state is " << status() << std::endl;
      m_mutex.unlock();
      return false;
    }
    m_mutex.unlock();
    return true;
  }

  bool destroy()
  {
    m_mutex.lock();
    if( m_fsm.process_event(pullerfsm::destroy())!=boost::msm::back::HANDLED_TRUE ){
      std::cout << "impossible to process destroy when state is " << status() << std::endl;
      m_mutex.unlock();
      return false;
    }
    m_mutex.unlock();
    return true;
  }
    
  bool reset()
  {
    m_mutex.lock();
    if( m_fsm.process_event(pullerfsm::reset())!=boost::msm::back::HANDLED_TRUE ){
      std::cout << "impossible to process reset when state is " << status() << std::endl;
      m_mutex.unlock();
      return false;
    }
    m_mutex.unlock();
    return true;
  }

 private:
  boost::mutex m_mutex;
  pullerfsm::FSM m_fsm;
};

#endif
